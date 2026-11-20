# API модели

FastAPI слушает порт 8000. Vite проксирует запросы `/api` на этот порт. Формат данных — JSON. Документация запросов с диапазонами параметров доступна в Swagger по адресу `http://localhost:8000/docs`.

## Конфигурация

```json
{
  "n": 2,
  "intervals": [[1, 3], [2, 4]],
  "workers": 2,
  "capacity": 3,
  "meanService": 2,
  "limit": 100,
  "seed": 42
}
```

`intervals` содержит по одной паре `[a, b]` для каждого источника. Источники, ячейки и приборы в ответах нумеруются с единицы. Идентификатор заявки — строка вида `И1-2` (источник и порядковый номер). При отсутствии значения используется `null`. Идентификатор прогона — уникальная строка.

| Запрос | Тело | Ответ |
|---|---|---|
| `POST /api/simulations` | `{ configuration, demo? }` | 201, `{ id, snapshot }` |
| `GET /api/simulations/{id}` | — | `{ id, snapshot }` |
| `POST /api/simulations/{id}/step` | `{ count: 1..10 }`, по умолчанию один шаг | `{ id, snapshot, finished, result? }`. Итог возвращается после завершения. |
| `POST /api/simulations/{id}/run` | — | `{ id, snapshot, finished, result }` |
| `POST /api/auto` | `{ configuration, demo?, adaptive?, cap? }` | `result` |
| `POST /api/experiments` | `{ configuration, configurations?, price, workerHour, slotHour, secondsPerUnit }` | `{ rows, best, message }` |

`demo: true` запускает фиксированную трассу. `adaptive: true` включает подбор N с пилотом 100. `cap` задаёт верхнюю границу N от 100 до 50 000. В экспериментах можно передать 4–8 полных конфигураций. Без списка будут сравнены четыре конфигурации на основе `configuration`. `best` равен `null`, если ни одна не прошла критерии.

`snapshot` включает `modelTime`, `event`, `calendar`, `actions`, `lastEviction`, `sources`, `slots`, `workers`, `workerPointer`, `generated`, `waiting`, `running`, `completed`, `rejected`, `loss`, `history` и `finished`. Поля `batch` и `last_batch` содержат текущий и последний закрытый пакет. События календаря `REQUEST_GENERATED` и `SERVICE_COMPLETED` упорядочены по времени, приоритету и очереди регистрации. `actions` и `history` показывают до 500 последних записей соответствующей выборки.

`result` включает `summary` (общие показатели и таблицы источников и приборов), `journal` (полный журнал прогона для экспорта), `attempts` (таблица подбора N) и `message` (пояснение к оценке).

При ошибке приходит `{ "detail": "…" }` с кодом 422 для неверных параметров или 404 для неизвестного прогона. Завершённый прогон доступен для чтения. Сервер хранит до 12 последних пошаговых прогонов в памяти. После перезапуска сервера требуется начать новый прогон.
