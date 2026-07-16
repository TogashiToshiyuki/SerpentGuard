# Three-minute demo script

This demo uses only the synthetic, redistributable files under `examples/demo/`.
They are deliberately simplified and are not production reactor models. Rehearse the
file picker and use short jump cuts between uploads so the public video remains under
three minutes without speeding through safety notices.

## Preparation

From an activated environment with the deterministic installation:

```powershell
python -m streamlit run app.py
```

For the optional live AI ending, install `.[ai]` and set `OPENAI_API_KEY` and
`SERPENTGUARD_OPENAI_MODEL` only in the launch shell. Keep the terminal, environment,
and browser address history out of frame. The local payload preview and consent gate
can be demonstrated without making a live request.

Use English for the main recording unless Japanese is central to the story; capture
one separate Japanese screenshot. Keep the Uploaded file bundle mode selected so no
absolute local path appears.

## Timed sequence

| Time | Action | Narration point |
| --- | --- | --- |
| 0:00–0:15 | Show the title, experimental disclaimer, local-analysis notice, language selector, and workflow line. | “SerpentGuard is a local preflight assistant for a deliberately limited Serpent subset; it does not replace Serpent or safety review.” |
| 0:15–0:30 | Upload `01_valid_minimal.inp`, press Run check, and show zero findings. | “Parsing and deterministic checks run only after the explicit action.” |
| 0:30–0:48 | Upload `02_undefined_surface.inp`; show SG004 and expand its evidence. | “Findings retain canonical rule IDs plus source file and line.” |
| 0:48–1:02 | Upload `03_contradictory_region.inp`; show SG008 WARNING. | “Contradictory signs are checked locally without AI.” |
| 1:02–1:38 | Upload `04_pwr_pin_cell.inp`; run it, sample Universe `0` with x/y `[-0.75, 0.75]` and resolution `121`, then show Material-colored Geometry view and briefly switch to Diagnostic view. | “The Geometry view distinguishes fuel, clad, coolant, and outside; the Diagnostic view is a separate sampling map.” |
| 1:38–2:02 | Upload `05_overlap_and_gap.inp`; sample Universe `0` with x/y `[-0.8, 0.8]` and resolution `121`; open Diagnostic view. | “This deliberately faulty synthetic case has both supported overlap and undefined candidates. Sampling can miss narrow defects.” |
| 2:02–2:20 | Upload `06_detector_issues.inp`; show SG021–SG024. | “Only selected `det` and `ene` options are checked; SerpentGuard does not judge detector physics.” |
| 2:20–2:52 | Upload `07_ai_review.inp`, set the purpose from its README, run, show the sanitized JSON preview, select consent, and optionally press Generate. | “Raw input, comments, compositions, paths, and keys are excluded. The call is optional and occurs only after preview, consent, and Generate.” |
| 2:52–2:59 | Return to deterministic findings and disclaimer. | “AI explains structured findings; it never replaces them or establishes physical validity.” |

If the network or API configuration is not dependable, stop after showing the disabled
Generate button, payload preview, and consent transition. Do not hide or edit an API
error in a way that implies a successful live request.

## Visual acceptance checks

- The PWR fixture shows a circular fuel region, annular clad, surrounding coolant,
  and outside rather than a single diagnostic color.
- Geometry view and Diagnostic view are visibly different and separately labeled.
- The legend is categorical, axes have equal scale, and no continuous colorbar is used.
- Japanese plot labels render with Yu Gothic or Meiryo on the developer Windows
  machine; otherwise the documented font warning is visible.
- Findings remain readable at video resolution and the selected rule ID is visible.
- No private source name, absolute path, username, API key, or environment value is on
  screen.

## Screenshot instructions

Capture from the synthetic demo only, preferably at a consistent browser width:

1. **Overview:** title, workflow, local-analysis notice, and clean summary.
2. **Deterministic finding:** SG004 row and its evidence expander, with the synthetic
   filename visible.
3. **Geometry:** PWR Material-colored Geometry view with legend and Universe `0`.
4. **Diagnostics:** overlap/gap Diagnostic view with its candidate metrics.
5. **Privacy/AI:** payload preview plus unchecked consent and disabled Generate button;
   crop before any shell or browser history is visible.
6. **Japanese:** the PWR Geometry view after selecting `日本語`, confirming readable
   plot title and legend.

Before capture, clear prior local-project text fields, use uploaded-bundle mode, close
terminals containing environment variables, and inspect every visible JSON field.
Never use private Serpent or PBED files in submission media.

## Devpost submission checklist

The target is the **OpenAI Build Week – Developer tools** track. Requirements were
checked on 2026-07-16; re-check the live pages before submission:

- [ ] Project name, tagline, category, and coherent description.
- [ ] Public project story explaining problem, local deterministic solution, optional
  privacy-preserving OpenAI explanation, impact, and limitations.
- [ ] Repository URL. Keep it public with the MIT license, or if private share it with
  the addresses named by the current rules.
- [ ] README setup/sample data/test instructions verified from a clean environment.
- [ ] Public YouTube video shorter than three minutes, with audio explaining Codex and
  GPT-5.6 usage accurately.
- [ ] Screenshots from the synthetic fixtures only.
- [ ] Honest Codex usage description: inspect-first milestone implementation,
  test-driven corrections, privacy boundary, and documentation/release audit.
- [ ] Confirm the qualifying Codex model/session metadata; do not claim GPT-5.6 unless
  the session actually used it.
- [ ] Run `/feedback` in the Codex session where most core functionality was built and
  paste that Session ID into the submission form. Do not invent or substitute a task
  URL.
- [ ] Known limitations and the experimental/non-safety disclaimer.
- [ ] Final proofread in Devpost's View page and eligibility/rules re-check.

Current authoritative pages:

- [OpenAI Build Week challenge](https://openai.devpost.com/)
- [OpenAI Build Week overview](https://openai.com/build-week/)
- [Devpost submission steps](https://help.devpost.com/article/126-know-your-submission-steps)
