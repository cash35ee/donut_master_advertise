"""
Donut
Copyright (c) 2022-present NAVER Corp.
MIT License
"""
import argparse
import json
import os
import re
import csv
from pathlib import Path

import numpy as np
import torch
from datasets import load_dataset
from PIL import Image
from tqdm import tqdm
import os

from donut import DonutModel, JSONParseEvaluator, load_json, save_json
def generate_csv_path(task_name):
    """
    自動生成CSV儲存路徑，格式為 output_<task_name>_YYYYMMDD_HHMMSS.csv
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_name = task_name if task_name else "test"
    filename = f"output_{task_name}_{timestamp}.csv"
    return os.path.join(os.getcwd(), filename)


def test(args):
    pretrained_model = DonutModel.from_pretrained(args.pretrained_model_name_or_path)

    if torch.cuda.is_available():
        pretrained_model.half()
        pretrained_model.to("cuda")

    pretrained_model.eval()

    if args.save_path:
        os.makedirs(os.path.dirname(args.save_path), exist_ok=True)

    predictions = []
    ground_truths = []
    accs = []

    evaluator = JSONParseEvaluator()
    dataset = load_dataset(args.dataset_name_or_path, split=args.split)

    for idx, sample in tqdm(enumerate(dataset), total=len(dataset)):
        ground_truth = json.loads(sample["ground_truth"])

        if args.task_name == "docvqa":
            output = pretrained_model.inference(
                image=sample["image"],
                prompt=f"<s_{args.task_name}><s_question>{ground_truth['gt_parses'][0]['question'].lower()}</s_question><s_answer>",
            )["predictions"][0]
        else:
            output = pretrained_model.inference(image=sample["image"], prompt=f"<s_{args.task_name}>")["predictions"][0]

        if args.task_name == "rvlcdip":
            gt = ground_truth["gt_parse"]
            score = float(output["class"] == gt["class"])
        elif args.task_name == "docvqa":
            gt = ground_truth["gt_parses"]
            answers = set([qa_parse["answer"] for qa_parse in gt])
            score = float(output["answer"] in answers)
        else:
            gt = ground_truth["gt_parse"]
            score = evaluator.cal_acc(output, gt)

        accs.append(score)

        predictions.append(output)
        ground_truths.append(gt)

    scores = {
        "ted_accuracies": accs,
        "ted_accuracy": np.mean(accs),
        "f1_accuracy": evaluator.cal_f1(predictions, ground_truths),
    }
    print(
        f"Total number of samples: {len(accs)}, Tree Edit Distance (TED) based accuracy score: {scores['ted_accuracy']}, F1 accuracy score: {scores['f1_accuracy']}"
    )

    # 自動產生 CSV 路徑
    if args.save_path:
        csv_path = os.path.splitext(args.save_path)[0] + ".csv"
    else:
        csv_path = generate_csv_path(args.task_name)

    # 儲存CSV: 預測與標註在各自欄位
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["prediction", "ground_truth"])  # 表頭
        for p, g in zip(predictions, ground_truths):
            # 將dict轉為字串
            p_str = json.dumps(p, ensure_ascii=False)
            g_str = json.dumps(g, ensure_ascii=False)
            writer.writerow([p_str, g_str])

    print(f"Predictions and ground truths saved to: {csv_path}")
    return predictions


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretrained_model_name_or_path", type=str)
    parser.add_argument("--dataset_name_or_path", type=str)
    parser.add_argument("--split", type=str, default="test")
    parser.add_argument("--task_name", type=str, default=None)
    parser.add_argument("--save_path", type=str, default=None)
    args, left_argv = parser.parse_known_args()

    if args.task_name is None:
        args.task_name = os.path.basename(args.dataset_name_or_path)

    predictions = test(args)

    # final_scores = evaluate(predictions, ground_truths)
    # print("======== Evaluation Results ========")
    # for k, v in final_scores.items():
    #     print(f"{k}: {v:.4f}" if v is not None else f"{k}: N/A")                                            