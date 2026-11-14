# Entrega — Consolidador de Reservas de Hotel (Onfly)

## 1. Defeitos corrigidos e causa raiz

Foram identificados e corrigidos **5 defeitos** no CLI:

1. **Filtro de status faturável incorreto (`src/onfly_report/services/status_policy.py`):**
   * **Causa raiz:** A função `is_billable` verificava `status != "CANCELLED"`, incluindo indevidamente reservas com status `NO_SHOW` nos cálculos de noites, valores financeiros, `by_month` e `top_hotels`, quando apenas `CONFIRMED` deveria ser faturável.
2. **Cálculo de noites quebrando na virada de mês/ano (`src/onfly_report/services/stay_calculator.py`):**
   * **Causa raiz:** A função `calculate_room_nights` subtraía apenas o número do dia do mês (`checkout.day - checkin.day`) em vez de subtrair os objetos `date` completos (`(checkout - checkin).days`), gerando valores negativos ou incorretos quando a estadia cruzava meses ou anos.
3. **Conversão cambial invertida e com perda de precisão (`src/onfly_report/services/currency_converter.py`):**
   * **Causa raiz:** A função `convert_to_brl` dividia o valor pela taxa convertendo ambos para `float` (`float(amount) / float(rate)`), violando a regra de negócio que exige multiplicação exata com `Decimal` (`amount * rate_to_brl`).
4. **Ordenação invertida no ranking de hotéis (`src/onfly_report/services/report_builder.py`):**
   * **Causa raiz:** O ranking `top_hotels` ordenava a chave `amount` de forma crescente (`(item[1]["amount"], item[0])`), quando o contrato exige ordenação decrescente por `total_brl` com desempate crescente por `hotel_id` (`(-item[1]["amount"], item[0])`).
5. **Truncamento silencioso na leitura do CSV de reservas (`src/onfly_report/repositories/csv_reservation_repository.py`):**
   * **Causa raiz:** O método `CsvReservationRepository.read()` possuía uma interrupção artificial (`if len(rows) == 200: break`) que descartava todas as reservas a partir da 201ª linha, fazendo o relatório ignorar 100 das 300 reservas de `data/reservas_hoteis.csv`.

---

## 2. Como o problema foi investigado e abordado

1. **Execução inicial da suíte de testes:** Ao rodar `pytest -q`, os 5 testes fornecidos falharam, apontando divergências nos cálculos de câmbio, noites na virada de mês, filtro de status e ordenação do ranking de hotéis.
2. **Inspeção ponta a ponta do pipeline:** Seguindo a ordem de processamento definida na especificação (`ler -> converter tipos -> contar status -> filtrar CONFIRMED -> agregar`), todos os módulos em `src/onfly_report/repositories/` e `src/onfly_report/services/` foram revisados linha a linha contra as regras do `README.md`.
3. **Descoberta do truncamento no repositório:** Embora os 5 testes originais usassem amostras pequenas (< 200 linhas), a revisão de `csv_reservation_repository.py` revelou a trava `if len(rows) == 200: break`, que afetava diretamente o arquivo principal `data/reservas_hoteis.csv` (300 reservas).
4. **Validação cruzada e ampliação da cobertura de testes:** Após aplicar as correções pontuais mantendo a precisão com `Decimal` e arredondamento `ROUND_HALF_UP` apenas na serialização, o resultado foi validado contra a amostra `data/exemplo-validacao.csv` e foram adicionados 6 novos testes em `tests/test_extra.py` cobrindo leitura acima de 200 linhas, desempate por `hotel_id`, virada de ano, ausência de reservas confirmadas e códigos de saída do CLI (`exit code 2`).

---

## 3. Como validar

### Pré-requisitos e instalação
```bash
python3.11 -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

pip install -r requirements-dev.txt
```

### Executar testes e linter
```bash
pytest -v
ruff check .
```

### Executar na amostra de validação
```bash
PYTHONPATH=src python -m onfly_report \
  --input data/exemplo-validacao.csv \
  --rates data/taxas_cambio.csv \
  --output output/exemplo.json
```
Saída no stdout:
```text
Reservas: 12 | Confirmadas: 9 | Noites: 28 | Total BRL: 7566.00
```

### Executar na base completa de reservas
```bash
PYTHONPATH=src python -m onfly_report \
  --input data/reservas_hoteis.csv \
  --rates data/taxas_cambio.csv \
  --output output/report.json
```
Saída no stdout:
```text
Reservas: 300 | Confirmadas: 187 | Noites: 907 | Total BRL: 344792.41
```

---

## 4. Resultado do `pytest` e testes adicionais (`tests/test_extra.py`)

Além dos **5 testes originais** (mantidos inalterados), foram adicionados **6 novos testes** em `tests/test_extra.py` para cobrir limites e regras de negócio que não eram testados inicialmente:
* **`test_reads_more_than_200_reservations`:** valida a leitura de 250 reservas sem truncar na linha 200.
* **`test_top_hotels_tie_breaker_by_hotel_id_ascending`:** valida o desempate de `top_hotels` por `hotel_id` ascendente em valores iguais.
* **`test_nights_across_year_boundary_and_by_month_order`:** valida estadias na virada de ano, múltiplos quartos e ordenação de `by_month`.
* **`test_zero_confirmed_reservations_avoids_division_by_zero`:** garante `"average_nightly_rate_brl": "0.00"` quando não há reservas confirmadas.
* **`test_cli_exit_code_2_on_missing_input_file` e `test_cli_exit_code_2_on_invalid_top_argument`:** validam o código de saída `2` do CLI para entradas ou argumentos inválidos.


```text
============================= test session starts =============================
collected 11 items

tests/test_currency.py::test_currency_conversion_to_brl PASSED           [  9%]
tests/test_extra.py::test_reads_more_than_200_reservations PASSED        [ 18%]
tests/test_extra.py::test_top_hotels_tie_breaker_by_hotel_id_ascending PASSED [ 27%]
tests/test_extra.py::test_nights_across_year_boundary_and_by_month_order PASSED [ 36%]
tests/test_extra.py::test_zero_confirmed_reservations_avoids_division_by_zero PASSED [ 45%]
tests/test_extra.py::test_cli_exit_code_2_on_missing_input_file PASSED   [ 54%]
tests/test_extra.py::test_cli_exit_code_2_on_invalid_top_argument PASSED [ 63%]
tests/test_nights.py::test_nights_across_month_boundary PASSED           [ 72%]
tests/test_regression_report.py::test_regression_report_on_sample PASSED [ 81%]
tests/test_status_rules.py::test_status_rules_exclude_cancelled_and_no_show PASSED [ 90%]
tests/test_top_hotels.py::test_top_hotels_are_ranked_descending PASSED   [100%]

============================= 11 passed in 0.85s ==============================
```
