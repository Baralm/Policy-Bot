# Eval report (25 questions: 18 answerable, 7 unanswerable)
Mode: HTTP http://localhost:8002/ask

## Retrieval quality
- section_recall (required passages cited): 100%
- hit_rate (>=1 required passage cited): 100%
- doc_recall: 100%
- citation_precision (cited passages relevant): 96%
- unanswerable_with_spurious_citations: 0%

## Answer quality
- overall_accuracy: 100%
- answerability_accuracy: 100%
- answerable_fact_accuracy: 100%
- conflict_question_accuracy: 100%
- abstention_recall (unanswerable -> false): 100%
- abstention_precision: 100%
- answers_with_citation: 100%

## Per question
| id | tags | gold | pred | correct | section recall | missing facts |
|---|---|---|---|---|---|---|
| Q01 | conflict | True | True | yes | 100% |  |
| Q02 | conflict,vehicle-type | True | True | yes | 100% |  |
| Q03 | conflict | True | True | yes | 100% |  |
| Q04 | conflict | True | True | yes | 100% |  |
| Q05 | conflict | True | True | yes | 100% |  |
| Q06 | single | True | True | yes | 100% |  |
| Q07 | vehicle-type | True | True | yes | 100% |  |
| Q08 | single | True | True | yes | 100% |  |
| Q09 | single | True | True | yes | 100% |  |
| Q10 | single | True | True | yes | 100% |  |
| Q11 | single | True | True | yes | 100% |  |
| Q12 | single | True | True | yes | 100% |  |
| Q13 | single | True | True | yes | 100% |  |
| Q14 | single | True | True | yes | 100% |  |
| Q15 | single | True | True | yes | 100% |  |
| Q16 | single | True | True | yes | 100% |  |
| Q17 | conflict,vehicle-type | True | True | yes | 100% |  |
| Q18 | robustness | True | True | yes | 100% |  |
| U01 | unanswerable,outside-knowledge | False | False | yes | n/a |  |
| U02 | unanswerable | False | False | yes | n/a |  |
| U03 | unanswerable,near-miss | False | False | yes | n/a |  |
| U04 | unanswerable | False | False | yes | n/a |  |
| U05 | unanswerable,near-miss | False | False | yes | n/a |  |
| U06 | unanswerable,outside-knowledge | False | False | yes | n/a |  |
| U07 | unanswerable,ambiguous | False | False | yes | n/a |  |
