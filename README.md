# APS - Rendering Task Processing Service

**Калашян Артур**, гр. **5130904/40102**, вариант **24**.

Первичные артефакты по АПС. Моделируется центр обработки заданий рендеринга: рабочие станции и сервисы отправляют задания, они ожидают в ограниченном буфере и обрабатываются вычислительными узлами. При переполнении возможен отказ заявки.

## Вариант СМО

`ИБ ИЗ2 ПЗ1 Д1ОЗ3 Д1ОО2 Д2П2 Д2Б5 ОР1 ОД3`

| Код | Правило |
|---|---|
| ИБ, ИЗ2 | Бесконечные источники, равномерные интервалы генерации |
| ПЗ1 | Экспоненциальное время обслуживания |
| Д1ОЗ3 | Первая свободная ячейка буфера без сдвига |
| Д1ОО2 | Отказ по приоритету номера источника |
| Д2П2 | Выбор свободного прибора по кольцу |
| Д2Б5 | Приоритетные пакеты заявок одного источника |
| ОР1, ОД3 | Сводная статистика, пошаговая динамика |

При освобождении прибора фиксируется пакет из ожидающих заявок выбранного источника. Он не пополняется новыми заявками; пока пакет не завершён, приборы работают только с ним.

## Диаграммы

| Диаграмма | PlantUML | Просмотр |
|---|---|---|
| Основной сценарий | [main-flow.puml](diagrams/sequence/main-flow.puml) | [SVG](previews/main-flow.svg) |
| Happy Flow | [happy-flow.puml](diagrams/sequence/happy-flow.puml) | [SVG](previews/happy-flow.svg) |
| Переполнение буфера | [overflow.puml](diagrams/sequence/overflow.puml) | [SVG](previews/overflow.svg) |
| Пакетная обработка | [batch-processing.puml](diagrams/sequence/batch-processing.puml) | [SVG](previews/batch-processing.svg) |
| Диаграмма классов | [class-diagram.puml](diagrams/class/class-diagram.puml) | [SVG](previews/class-diagram.svg) |
| Flowchart с дорожками | [system-flow.puml](diagrams/flowchart/system-flow.puml) | [SVG](previews/system-flow.svg) |
