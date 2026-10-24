"""Optional Google Calendar integration for the daily reminders."""

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, time, timedelta

from django.conf import settings
from django.utils import timezone

from .models import DailyReminder

TOKEN_URL = 'https://oauth2.googleapis.com/token'
EVENTS_URL = 'https://www.googleapis.com/calendar/v3/calendars/primary/events'
CLIENT_ID_ENV = 'GOOGLE_CLIENT_ID'
CLIENT_SECRET_ENV = 'GOOGLE_CLIENT_SECRET'
REFRESH_TOKEN_ENV = 'GOOGLE_REFRESH_TOKEN'
REQUIRED_ENV = (CLIENT_ID_ENV, CLIENT_SECRET_ENV, REFRESH_TOKEN_ENV)
ALL_DAY_LABEL = 'Dia inteiro'
UNTITLED_EVENT = '(sem título)'
TITLE_MAX_LENGTH = DailyReminder._meta.get_field('title').max_length
NOT_CONFIGURED = 'Google Calendar não configurado'
TOKEN_ERROR = 'falha ao renovar o token do Google Calendar'
INVALID_RESPONSE = 'resposta inválida do Google Calendar'
MISSING_EVENT_ID = 'evento sem id ignorado na agenda'
WRITE_ERROR = 'falha ao gravar o lembrete do evento'
DELETE_ERROR = 'falha ao remover lembretes do Google Calendar'
ACCESS_TOKEN_PATTERN = re.compile(r'ya29\.[A-Za-z0-9._~+/=-]+')
HIDDEN = '***'


class CalendarSyncError(Exception):
    """Failure while talking to the Google Calendar API."""


def _read_json(request, timeout):
    """Fetch ``request`` and decode its body as JSON."""
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as error:
        raise CalendarSyncError(f'HTTP {error.code}')
    except urllib.error.URLError as error:
        raise CalendarSyncError(f'falha de rede: {error.reason}')
    except (TimeoutError, OSError) as error:
        raise CalendarSyncError(f'falha de rede: {error}')
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        raise CalendarSyncError(INVALID_RESPONSE)


def _parse_datetime(raw):
    """Parse an RFC3339 timestamp into a local aware ``datetime``."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    if text.endswith('Z'):
        text = f'{text[:-1]}+00:00'
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.get_current_timezone())
    return timezone.localtime(moment)


def _scheduled_time(event):
    """Return the ``time`` stored for one already parsed event."""
    if event['is_all_day']:
        return time.min
    try:
        return datetime.strptime(event['time_label'], '%H:%M').time()
    except (TypeError, ValueError):
        return time.min


class GoogleCalendarSyncService:
    """Read today's Google Calendar events and mirror them as reminders.

    The integration is optional: without the three OAuth2 environment
    variables ``is_configured`` is ``False`` and every method degrades to
    an empty result. Network and API problems are reported in
    ``last_error`` and in the ``errors`` key of the sync result; they are
    never raised to the caller. Credentials are stripped from every
    message before it leaves the service.
    """

    def __init__(self, user, timeout=10):
        self.user = user
        self.timeout = timeout
        self.last_error = ''
        self._cached_token = ''

    @property
    def is_configured(self):
        """Whether the three OAuth2 variables are available."""
        return all(self._env(name) for name in REQUIRED_ENV)

    def todays_events(self):
        """Return today's events as dicts, ordered by schedule.

        Each dict carries ``id``, ``title``, ``time_label``,
        ``is_all_day`` and ``html_link``. Without configuration, or on
        any network/HTTP/JSON failure, the list is empty and the reason
        is left in ``last_error``.
        """
        self.last_error = ''
        if not self.is_configured:
            self.last_error = NOT_CONFIGURED
            return []
        try:
            payload = _read_json(self._events_request(), self.timeout)
        except Exception as error:  # noqa: BLE001 - never raised to callers
            self.last_error = self._sanitize(error)
            return []
        items = payload.get('items') if isinstance(payload, dict) else None
        if not isinstance(items, list):
            items = []
        parsed = [self._parse_event(item) for item in items]
        events = [item for item in parsed if item is not None]
        events.sort(key=lambda item: (item[0], item[1]))
        return [item[2] for item in events]

    def sync_today(self):
        """Mirror today's events into ``DailyReminder`` rows.

        Reminders typed by the user (``external_google_event_id`` empty)
        are never created, changed or deleted by this method. A failed
        read of the agenda aborts the sync instead of deleting anything,
        so a network hiccup cannot wipe the mirrored reminders.
        """
        result = {'created': 0, 'updated': 0, 'deleted': 0, 'errors': []}
        if not self.is_configured:
            self.last_error = NOT_CONFIGURED
            return result
        events = self.todays_events()
        if self.last_error:
            result['errors'].append(self.last_error)
            return result

        today = timezone.localdate()
        mirrored_ids = []
        for event in events:
            if not event['id']:
                result['errors'].append(MISSING_EVENT_ID)
                continue
            mirrored_ids.append(event['id'])
            try:
                created = self._mirror(event, today)
            except Exception as error:  # noqa: BLE001 - reported, not raised
                result['errors'].append(
                    self._sanitize(f'{WRITE_ERROR}: {error}')
                )
                continue
            result['created' if created else 'updated'] += 1

        result['deleted'] = self._drop_stale(today, mirrored_ids, result)
        return result

    def _mirror(self, event, today):
        """Create or refresh the reminder that mirrors one event."""
        _, created = DailyReminder.objects.update_or_create(
            user=self.user,
            external_google_event_id=event['id'],
            defaults={
                'title': event['title'][:TITLE_MAX_LENGTH],
                'scheduled_time': _scheduled_time(event),
                'reminder_date': today,
            },
        )
        return created

    def _drop_stale(self, today, mirrored_ids, result):
        """Delete the mirrored reminders that left today's agenda."""
        stale = DailyReminder.objects.filter(
            user=self.user,
            reminder_date=today,
        ).exclude(external_google_event_id='')
        if mirrored_ids:
            stale = stale.exclude(
                external_google_event_id__in=mirrored_ids,
            )
        try:
            deleted, _ = stale.delete()
        except Exception as error:  # noqa: BLE001 - reported, not raised
            result['errors'].append(self._sanitize(f'{DELETE_ERROR}: {error}'))
            return 0
        return deleted

    def _events_request(self):
        """Build the authenticated request for today's events."""
        _, start, end = self._day_bounds()
        query = urllib.parse.urlencode(
            {
                'timeMin': start.isoformat(),
                'timeMax': end.isoformat(),
                'singleEvents': 'true',
                'orderBy': 'startTime',
                'timeZone': settings.TIME_ZONE,
            }
        )
        return urllib.request.Request(
            f'{EVENTS_URL}?{query}',
            headers={
                'Accept': 'application/json',
                'Authorization': f'Bearer {self._access_token()}',
            },
        )

    def _access_token(self):
        """Return the cached access token, asking Google once per run."""
        if self._cached_token:
            return self._cached_token
        body = urllib.parse.urlencode(
            {
                'grant_type': 'refresh_token',
                'client_id': self._env(CLIENT_ID_ENV),
                'client_secret': self._env(CLIENT_SECRET_ENV),
                'refresh_token': self._env(REFRESH_TOKEN_ENV),
            }
        ).encode('utf-8')
        request = urllib.request.Request(
            TOKEN_URL,
            data=body,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json',
            },
            method='POST',
        )
        try:
            payload = _read_json(request, self.timeout)
        except CalendarSyncError as error:
            raise CalendarSyncError(f'{TOKEN_ERROR}: {error}')
        token = ''
        if isinstance(payload, dict):
            token = payload.get('access_token')
        if not isinstance(token, str) or not token.strip():
            raise CalendarSyncError(f'{TOKEN_ERROR}: {INVALID_RESPONSE}')
        self._cached_token = token.strip()
        return self._cached_token

    @staticmethod
    def _parse_event(item):
        """Turn one API item into ``(sort time, sort title, dict)``."""
        if not isinstance(item, dict):
            return None
        start = item.get('start')
        if not isinstance(start, dict):
            start = {}
        moment = _parse_datetime(start.get('dateTime'))
        scheduled = moment.time() if moment is not None else time.min
        title = str(item.get('summary') or '').strip() or UNTITLED_EVENT
        event = {
            'id': str(item.get('id') or '').strip(),
            'title': title,
            'time_label': (
                scheduled.strftime('%H:%M')
                if moment is not None
                else ALL_DAY_LABEL
            ),
            'is_all_day': moment is None,
            'html_link': str(item.get('htmlLink') or '').strip(),
        }
        return scheduled, title.lower(), event

    @staticmethod
    def _day_bounds():
        """Return today and the aware start/end of the local day."""
        today = timezone.localdate()
        current = timezone.get_current_timezone()
        start = datetime.combine(today, time.min, tzinfo=current)
        end = datetime.combine(
            today + timedelta(days=1),
            time.min,
            tzinfo=current,
        )
        return today, start, end

    @staticmethod
    def _env(name):
        """Return a stripped environment variable, empty when absent."""
        return (os.environ.get(name) or '').strip()

    def _sanitize(self, message):
        """Remove every credential from a message before it is stored.

        The cached token is dropped from the text, and any string that
        looks like a Google access token is masked as well: a failure
        raised while the token request itself is in flight happens
        before the token is cached.
        """
        text = ACCESS_TOKEN_PATTERN.sub(HIDDEN, str(message))
        secrets = (
            self._cached_token,
            self._env(REFRESH_TOKEN_ENV),
            self._env(CLIENT_SECRET_ENV),
        )
        for secret in secrets:
            if secret:
                text = text.replace(secret, HIDDEN)
        return text
