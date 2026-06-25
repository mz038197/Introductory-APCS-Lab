"""Build _上繳.ipynb from a student lesson notebook using the submit template."""

import copy
import json
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "lab/student/Lesson1/IPO與程式結構(2)_上繳.ipynb"

APCS_HEADER_RE = re.compile(r"### .*?APCS (\d+-\d+[a-z]?)\s")
SUBHEADER_RE = re.compile(r"#### APCS (\d+-\d+[a-z]?)\.py")
ZJ_A_RE = re.compile(r"### \*\*(a\d+)\.")
ZJ_ID_RE = re.compile(r"### \*\*\[?(c\d+|g\d+)\.")
PROBLEM_RE = re.compile(r"## Problem ([A-Z]) ")


def _cell_text(cell):
    src = cell.get("source", [])
    return src if isinstance(src, str) else "".join(src)


def _is_start_code_cell(cell):
    if cell.get("cell_type") != "code":
        return False
    text = _cell_text(cell).strip()
    if not text:
        return False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "#start" or stripped.startswith("#start-"):
            return True
    return False


def _parse_header_id(text: str, problem_counts: dict) -> str | None:
    m = APCS_HEADER_RE.search(text)
    if m:
        return f"APCS_{m.group(1)}"
    m = SUBHEADER_RE.search(text)
    if m:
        return f"APCS_{m.group(1)}"
    m = ZJ_A_RE.search(text)
    if m:
        return m.group(1)
    m = ZJ_ID_RE.search(text)
    if m:
        return m.group(1)
    m = PROBLEM_RE.search(text)
    if m:
        letter = m.group(1)
        problem_counts[letter] = problem_counts.get(letter, 0) + 1
        n = problem_counts[letter]
        return f"Prob_{letter}" if n == 1 else f"Prob_{letter}{n}"
    return None


def _collect_question_ids(cells):
    current_id = None
    pending = []
    result = []
    problem_counts = {}

    for i, cell in enumerate(cells):
        if cell.get("cell_type") == "markdown":
            qid = _parse_header_id(_cell_text(cell), problem_counts)
            if qid:
                if pending:
                    result.append(pending[-1])
                    pending.clear()
                current_id = qid

        if _is_start_code_cell(cell) and current_id:
            pending.append((i, current_id))

    if pending:
        result.append(pending[-1])

    return result


def _make_submit_md(template_md, lesson_title: str, example_id: str):
    cell = copy.deepcopy(template_md)
    cell["source"] = []
    for line in template_md["source"]:
        s = line.replace("IPO與程式結構", lesson_title).replace("APCS_3-1", example_id)
        cell["source"].append(s)
    return cell


def build_submit_notebook(
    src_path: Path,
    out_path: Path,
    lesson_title: str,
    example_id: str,
    insert_after: int = 1,
):
    with TEMPLATE.open(encoding="utf-8") as f:
        template = json.load(f)
    with src_path.open(encoding="utf-8") as f:
        src_nb = json.load(f)

    submit_md = _make_submit_md(template["cells"][2], lesson_title, example_id)
    setup_cells = [copy.deepcopy(template["cells"][i]) for i in (3, 4, 5)]

    submit_targets = {idx: qid for idx, qid in _collect_question_ids(src_nb["cells"])}

    new_cells = []
    for i, cell in enumerate(src_nb["cells"]):
        if i == insert_after:
            new_cells.append({"cell_type": "markdown", "metadata": {}, "source": ["---\n"]})
            new_cells.extend([submit_md, *setup_cells])

        if i in submit_targets:
            qid = submit_targets[i]
            new_cell = copy.deepcopy(cell)
            lines = _cell_text(cell).splitlines()
            new_lines = []
            replaced = False
            for line in lines:
                stripped = line.strip()
                if not replaced and (
                    stripped == "#start" or stripped.startswith("#start-")
                ):
                    new_lines.append(f"#start-{qid}")
                    replaced = True
                else:
                    new_lines.append(line)
            if not replaced:
                new_lines.insert(0, f"#start-{qid}")
            new_cell["source"] = "\n".join(new_lines) + ("\n" if new_lines else "")
            new_cell["outputs"] = []
            new_cell["execution_count"] = None
            new_cells.append(new_cell)
            new_cells.append(
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {"id": uuid.uuid4().hex[:12]},
                    "outputs": [],
                    "source": f'make_submit_button("{qid}")\n',
                }
            )
        else:
            new_cells.append(copy.deepcopy(cell))

    out_nb = copy.deepcopy(src_nb)
    out_nb["cells"] = new_cells
    out_nb["metadata"] = copy.deepcopy(template["metadata"])
    out_nb["metadata"].setdefault("colab", {}).update(
        {
            "authorship_tag": src_nb.get("metadata", {})
            .get("colab", {})
            .get("authorship_tag", ""),
            "provenance": [],
            "toc_visible": True,
        }
    )

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out_nb, f, ensure_ascii=False, indent=1)

    return len(submit_targets)


def main():
    jobs = [
        # Lesson2 (keep for re-run)
        (
            ROOT / "lab/student/Lesson2/流程控制_選擇條件(1).ipynb",
            ROOT / "lab/student/Lesson2/流程控制_選擇條件(1)_上繳.ipynb",
            "選擇條件",
            "APCS_4-1",
            1,
        ),
        (
            ROOT / "lab/student/Lesson2/流程控制_基礎迴圈(2).ipynb",
            ROOT / "lab/student/Lesson2/流程控制_基礎迴圈(2)_上繳.ipynb",
            "基礎迴圈",
            "APCS_5-1",
            1,
        ),
        # Lesson3
        (
            ROOT / "lab/student/Lesson3/基礎資料結構(1).ipynb",
            ROOT / "lab/student/Lesson3/基礎資料結構(1)_上繳.ipynb",
            "基礎資料結構",
            "APCS_6-1",
            1,
        ),
        (
            ROOT / "lab/student/Lesson3/條件、迴圈與串列應用(2).ipynb",
            ROOT / "lab/student/Lesson3/條件、迴圈與串列應用(2)_上繳.ipynb",
            "條件、迴圈與串列應用",
            "APCS_7-1a",
            1,
        ),
        (
            ROOT / "lab/student/Lesson3/Lesson3課堂實作_ZeroJudge(3).ipynb",
            ROOT / "lab/student/Lesson3/Lesson3課堂實作_ZeroJudge(3)_上繳.ipynb",
            "ZeroJudge",
            "a001",
            0,
        ),
        (
            ROOT / "lab/student/Lesson3/商業類術科精選_配合本Lesson.ipynb",
            ROOT / "lab/student/Lesson3/商業類術科精選_配合本Lesson_上繳.ipynb",
            "商業類術科精選",
            "Prob_G",
            0,
        ),
        # Lesson4
        (
            ROOT / "lab/student/Lesson4/函式與模組(1).ipynb",
            ROOT / "lab/student/Lesson4/函式與模組(1)_上繳.ipynb",
            "函式與模組",
            "APCS_8-1",
            1,
        ),
        (
            ROOT / "lab/student/Lesson4/字串應用(2).ipynb",
            ROOT / "lab/student/Lesson4/字串應用(2)_上繳.ipynb",
            "字串應用",
            "APCS_9-1",
            1,
        ),
        (
            ROOT / "lab/student/Lesson4/Lesson4程式實作-ZeroJudge(3).ipynb",
            ROOT / "lab/student/Lesson4/Lesson4程式實作-ZeroJudge(3)_上繳.ipynb",
            "ZeroJudge",
            "c295",
            0,
        ),
        (
            ROOT / "lab/student/Lesson4/商業類術科精選_配合本Lesson.ipynb",
            ROOT / "lab/student/Lesson4/商業類術科精選_配合本Lesson_上繳.ipynb",
            "商業類術科精選",
            "Prob_K",
            0,
        ),
    ]
    for src, out, title, example, insert_after in jobs:
        if not src.exists():
            print(f"SKIP missing {src.name}")
            continue
        n = build_submit_notebook(src, out, title, example, insert_after)
        print(f"Wrote {out.name} ({n} submit buttons)")


if __name__ == "__main__":
    main()
