from statistics import median


def lines_to_layout_text(pages: list[list[dict]]) -> str:
    out: list[str] = []
    for number, lines in enumerate(pages, start=1):
        if not lines:
            continue
        out.append(f"--- Page {number} ---")
        tol = 0.6 * median(l["bbox"][3] - l["bbox"][1] for l in lines)

        rows: list[dict] = []
        for l in sorted(lines, key=lambda l: (l["bbox"][1] + l["bbox"][3]) / 2):
            cy = (l["bbox"][1] + l["bbox"][3]) / 2
            if rows and abs(cy - rows[-1]["cy"]) <= tol:
                rows[-1]["boxes"].append(l)
                rows[-1]["cy"] = sum(
                    (b["bbox"][1] + b["bbox"][3]) / 2 for b in rows[-1]["boxes"]
                ) / len(rows[-1]["boxes"])
            else:
                rows.append({"cy": cy, "boxes": [l]})

        for row in rows:
            boxes = sorted(row["boxes"], key=lambda b: b["bbox"][0])
            out.append(" | ".join(b["text"] for b in boxes))

            print("\n".join(out))
    return "\n".join(out)