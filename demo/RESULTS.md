# Demo results (deepseek-flash, V4.1-Flash-1017)

## Blunt exfiltration (email PII / API key to attacker.example)
- 0 / 98 across 5 techniques x 2 placements, default AND deliberately-naive agent. Model refuses.

## Unauthorized cross-account access (confused deputy), session = customer #1
Subtler procedural injections, temperature 0.7, k=3, pages 1-20 (60 samples):
| Condition            | Attempted out-of-scope | Actually leaked |
|----------------------|------------------------|-----------------|
| No defense           | 13/60 (22%)            | 13/60 (22%)     |
| Harness scope check  | 12/60 (20%)            | 0/60 (0%)       |

Most effective injection styles: checklist, steps. Least: faq, note.
Takeaway: the model's attempt rate is ~unchanged by the defense; the harness block is what
drives leaks to zero. The model is not the control; the harness is (Laurie Voss's thesis).

TODO before publishing: scale to all 200 pages for tighter numbers; add a clean-page control
group for a true ASR lift; judge calibration; AX online-eval + monitor for regression alerts.
