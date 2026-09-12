"""Record bounded AI visual observations made from 65 original files.

This serializes observations, not an automatic vision evaluation or an expert
annotation approval. Images were opened individually with view_image on
2026-09-12; no preview collage, altered dataset image or inference was saved.
"""

from pathlib import Path
import sys
import time

from validate_dataset_training import DATASET, RUN_ID, context, jsonl, locations, parse_annotations, sha256, write_json


# Review-session observations keyed by exact original image stem, not predictions.
OBSERVATIONS = {
    "test0213-roti": "Puffed browned flatbread over a flame; rotated black corners.",
    "test0463-poorna_kolukattai": "White dumpling-like items on tray; hand and text overlay.",
    "test1916-beetroot_poriyal": "Chopped red food with green garnish.",
    "test2472-rice": "White grains in blue bowl; rotated black borders.",
    "test2758-chicken_biryani": "Rice with large browned pieces in a dish.",
    "test3985-roti": "Triangular folded flatbreads on white plate; rotated borders.",
    "test4658-chicken_biryani": "Rice and browned pieces; large title and watermark.",
    "train0460-medu_vada": "Several golden fried ring-shaped items on platter.",
    "train10771-roti": "Folded flatbreads; rotated black borders.",
    "train10842-eggs": "Many halved egg-like items on black plate.",
    "train11010-carrot_poriyal": "Orange chopped or shredded food in white bowl; coarse pixels.",
    "train1116-rice": "White grains and metal spoon; rotated border.",
    "train11420-coconut_chutney": "Elongated crepe-like item with several sauces; mixed meal.",
    "train12329-beetroot_poriyal": "Red chopped food in white tray; stretched or rotated appearance.",
    "train13295-roti": "Browned round flatbread; rotated black borders.",
    "train13511-rice": "White grains in brown bowl; rotated border.",
    "train1467-rice": "Close-up white grains; rotated black borders.",
    "train14719-coconut_chutney": "Triangular crepe-like item with pale topping and multiple sauces; watermark.",
    "train14854-nandu_masala": "Claw-like pieces in sauce; watermark.",
    "train15440-rice": "White grains on wooden spoon and in pot; rotated borders.",
    "train16670-roti": "Browned round flatbread; rotated black corners.",
    "train17222-appam": "Two bowl-shaped crepe-like items and sauce; coarse pixels.",
    "train17878-poorna_kolukattai": "Composite of white filled dumpling-like items and halves; black bars.",
    "train19562-dosa": "Folded golden crepe-like item with two sauces.",
    "train20505-beetroot_poriyal": "Diced red food and herbs; coarse or stretched appearance.",
    "train21567-appam": "Pale porous crepe-like items.",
    "train21934-rice": "White grains in white bowl; rotated borders.",
    "train24133-dosa": "Mixed plate with rolled crepe-like item, white cakes, sauces and title.",
    "train24316-coconut_chutney": "Folded crepe-like item with pale pat, yellow side and white/red sauces.",
    "train24354-rice": "Three pots of brown and white grains; rotated borders.",
    "train26817-dosa": "Folded browned crepe-like items with green and orange sauces.",
    "train27689-rice": "White grains and wooden spoon; slightly rotated view.",
    "train27836-appam": "Two bowl-shaped browned crepe-like items and a bowl of sauce; coarse pixels.",
    "train27907-appam": "Several pale porous crepe-like items on green surface.",
    "train28061-beetroot_poriyal": "Chopped red pieces with green garnish; stretched or coarse appearance.",
    "train28105-beetroot_poriyal": "Close-up red chopped food and small green pieces; pronounced vertical stretching.",
    "train28115-beetroot_poriyal": "Red shredded food in white dish; stretched appearance.",
    "train28773-carrot_poriyal": "Orange and yellow chopped pieces in white bowl; coarse stretched appearance.",
    "train2900-dosa": "Two overlapping golden folded crepe-like items on white plate.",
    "train30254-dosa": "Golden rolled crepe-like item with separate green and orange sauces.",
    "train30335-coconut_chutney": "Long rolled crepe-like item and three colored sauces; black background.",
    "train30343-coconut_chutney": "Folded crepe-like item with pale pat, yellow side and white/red sauces.",
    "train30368-dosa": "Browned crepe-like item on green leaf with several sides behind; dim scene.",
    "train30378-dosa": "Mixed plate with rolled crepe-like item, white cakes and sauces; title overlay.",
    "train32902-nandu_masala": "Shell and claw-like pieces in sauce; watermark.",
    "train32929-nandu_masala": "Shell and claw-like pieces in white bowl; text overlay and stretched appearance.",
    "train3443-rice": "White grains with metal spoon; rotated black borders.",
    "train34625-poorna_kolukattai": "White filled dumpling-like items on dark tray; watermark.",
    "train34678-poorna_kolukattai": "Composite of white filled dumpling-like items and halves; black bars.",
    "train5055-nandu_masala": "Shell and claw-like pieces in white bowl; text overlay and stretched appearance.",
    "train6279-poorna_kolukattai": "White filled dumpling-like items on dark tray; watermark.",
    "train6305-roti": "Stacked flatbreads; rotated black corners.",
    "train7487-dosa": "Browned crepe-like item on green leaf with several sides behind; dim scene.",
    "train8418-sambar": "Triangular browned crepe-like item and two bowls of sauce; watermark.",
    "train8464-beetroot_poriyal": "Close-up red chopped food and small green pieces; pronounced vertical stretching.",
    "train8977-rice": "Close-up white grains; rotated black corners.",
    "train9820-rice": "White grains on blue plate with fork; rotated black corners.",
    "train9901-roti": "Puffed flatbread on wire rack; rotated black corners.",
    "valid0310-mutton_biryani": "Rice and large browned pieces in metal pot; coarse pixels.",
    "valid2002-chicken_biryani": "Rice and large pieces; person inset, large title and watermark.",
    "valid2465-parupu_vadai": "Golden coarse-textured oval fried items with green pieces on plate.",
    "valid3235-coconut_chutney": "Browned rolled crepe-like item, pale pat and green sauce.",
    "valid4534-dosa": "Two folded golden crepe-like items and separate green/red sauces.",
    "valid4749-carrot_poriyal": "Orange chopped pieces with green pieces; stretched coarse appearance.",
    "valid4805-nandu_masala": "Shell and claw-like pieces and green garnish in white dish.",
}


def main():
    local, reports = locations(RUN_ID)
    report, started = context(), time.monotonic()
    flagged = [row for row in jsonl(local / "split-manifest.jsonl") if row["issues"]]
    if {Path(row["path"]).stem for row in flagged} != set(OBSERVATIONS):
        raise ValueError("Frozen flagged-image inventory differs from visual review notes")
    records = []
    for row in flagged:
        image = DATASET / row["path"]
        label = image.parent.parent / "labels" / (image.stem + ".txt")
        if sha256(image) != row["sha256"] or sha256(label) != row["label_sha256"]:
            raise ValueError("Image or annotation differs from frozen review inventory")
        records.append({"path": row["path"], "sha256": row["sha256"], "label_sha256": row["label_sha256"],
                        "observation": OBSERVATIONS[image.stem], "food_visually_present": True,
                        "annotation_records": parse_annotations(label.read_text(), 72),
                        "expert_class_and_box_adjudication": "pending"})
    report.update({"run_id": RUN_ID, "command": [sys.executable, str(Path(__file__))], "exit_code": 0,
                   "status": "ai_original_image_inspection_complete_expert_review_pending",
                   "recording_duration_seconds_not_visual_review_duration": round(time.monotonic() - started, 3),
                   "review_date": "2026-09-12", "reviewer_type": "AI assistant, not independent qualified human annotator",
                   "reviewed_original_images": len(records), "records": records,
                   "conclusion": "Food is visibly present in all 65 flagged images; an invalid box is not evidence of a negative scene.",
                   "limitations": ["This is a descriptive review, not a semantic annotation correctness rate or recipe confirmation.",
                                   "Existing boxes were read numerically but no corrected boxes or labels were drawn or saved.",
                                   "Visual stretching, overlays and repeated-looking scenes are observational flags, not verified augmentation lineage.",
                                   "No clinical judgment, image reuse permission or test independence is established.",
                                   "Original files were viewed individually; initial unsupported low-detail and truncated batches were re-viewed successfully before counting."]})
    write_json(reports / "dataset-visual-review.json", report)
    print(f"Recorded {len(records)} original-image observations; qualified human annotation review remains pending.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
