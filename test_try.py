import csv
import json
import argparse

#############################
# (A) 輔助函式
#############################

def parse_json_with_double_quotes_fix(s: str):
    s = s.strip()
    if len(s) >= 2 and s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    s = s.replace('""', '"')
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return {}

def exact_match(a, b):
    """若兩者字串完全相同則回傳1，否則0。"""
    return 1 if a == b else 0

def normalize_phone(phone_data):
    """
    將電話欄位轉成 list[str]。
    (若原本就是字串，包成單元素list；若是list, 去掉前後空白；其他型別則回傳空list)
    """
    if isinstance(phone_data, str):
        return [phone_data.strip()]
    elif isinstance(phone_data, list):
        return [p.strip() for p in phone_data]
    else:
        return []

def precision_recall(pred_phones, gt_phones):
    """
    簡易的電話 precision/recall 計算：set交集除以 set大小。
    """
    set_pred = set(pred_phones)
    set_gt   = set(gt_phones)
    matched  = set_pred.intersection(set_gt)
    precision = len(matched) / len(set_pred) if set_pred else 0.0
    recall    = len(matched) / len(set_gt)   if set_gt   else 0.0
    return precision, recall

def ensure_list(x):
    """若 x 不是 list，就包成 list；有些 JSON 可能會給單一職位 dict 而非陣列"""
    return x if isinstance(x, list) else [x]

#############################
# (B) 主體評分函式
#############################
def evaluate_predictions(all_predictions, all_labels):
    """
    對多筆 (pred, label) 做評分，回傳結構:
    {
      "field_accuracy": {
        "公司名稱": ...,
        "公司地址": ...,
        "聯絡電話 (precision)": ...,
        "聯絡電話 (recall)": ...,
        "職位名稱": ...,
        "工作地點": ...,
        "工作開始時間": ...,
        "工作結束時間": ...,
        "薪資下限": ...,
        "薪資上限": ...,
        "薪資方式": ...
      },
      "top_level_accuracy": ...,
      "job_level_accuracy": ...,
      "overall_accuracy": ...
    }
    """
    # -- 欄位定義 --
    TOP_LEVEL_FIELDS = ["公司名稱", "公司地址"]  # 不含電話
    JOB_FIELDS = [
        "職位名稱",
        "工作地點",
        "工作開始時間",
        "工作結束時間",
        "薪資下限",
        "薪資上限",
        "薪資方式"
    ]
    # 注意: "其他資訊" 若不計算, 就不加入

    # 用來計算 field_accuracy 的 correct/total
    field_correct = {
        "公司名稱": 0, "公司地址": 0,
        "職位名稱": 0, "工作地點": 0,
        "工作開始時間": 0, "工作結束時間": 0,
        "薪資下限": 0, "薪資上限": 0,
        "薪資方式": 0
    }
    field_total = {
        "公司名稱": 0, "公司地址": 0,
        "職位名稱": 0, "工作地點": 0,
        "工作開始時間": 0, "工作結束時間": 0,
        "薪資下限": 0, "薪資上限": 0,
        "薪資方式": 0
    }

    # top-level correct/total (只有公司名稱、公司地址)
    top_level_correct = 0
    top_level_total   = 0

    # job-level correct/total (包含 JOB_FIELDS 所有欄位，不含電話)
    job_level_correct = 0
    job_level_total   = 0

    # 電話計算 precision/recall
    phone_precision_sum = 0.0
    phone_recall_sum    = 0.0
    phone_count         = 0   # 有多少張廣告(筆數)要算電話p/r

    # 逐筆比較
    N = len(all_predictions)
    for i in range(N):
        pred = all_predictions[i]
        label= all_labels[i]

        # ========== A) 頂層比對 (公司名稱、公司地址) ==========
        for f in TOP_LEVEL_FIELDS:
            field_total[f] += 1
            top_level_total += 1
            if pred.get(f, "") == label.get(f, ""):
                field_correct[f] += 1
                top_level_correct += 1

        # ========== B) 聯絡電話 precision, recall ==========
        # (不納入 overall / top_level / job_level accuracy)
        if "聯絡電話" in pred and "聯絡電話" in label:
            phone_count += 1
            pred_phone = normalize_phone(pred["聯絡電話"])
            label_phone= normalize_phone(label["聯絡電話"])
            p, r = precision_recall(pred_phone, label_phone)
            phone_precision_sum += p
            phone_recall_sum    += r

        # ========== C) 職位比對 ==========
        #  先把 label, pred 的職位都確保是 list
        label_jobs = ensure_list(label.get("職位", []))
        pred_jobs  = ensure_list(pred.get("職位", []))

        # 以 index 對 index
        min_len = min(len(label_jobs), len(pred_jobs))
        for idx in range(min_len):
            lj = label_jobs[idx]
            pj = pred_jobs[idx]
            # 逐欄比對
            for jf in JOB_FIELDS:
                field_total[jf] += 1
                job_level_total += 1
                if lj.get(jf, "") == pj.get(jf, ""):
                    field_correct[jf] += 1
                    job_level_correct += 1

        # label 多出 or pred 多出 => 全算錯，但 total 要加
        if len(label_jobs) > len(pred_jobs):
            extra = len(label_jobs) - len(pred_jobs)
            for _ in range(extra):
                for jf in JOB_FIELDS:
                    field_total[jf] += 1
                    job_level_total += 1
        elif len(pred_jobs) > len(label_jobs):
            extra = len(pred_jobs) - len(label_jobs)
            for _ in range(extra):
                for jf in JOB_FIELDS:
                    field_total[jf] += 1
                    job_level_total += 1

    # ---------------------------------------------------------------------
    # (1) 計算各欄位的 accuracy (field_accuracy)
    def format_float(value):
        return round(value, 4)
    field_accuracy_dict={}
    

    # 公司名稱、公司地址
    field_accuracy_dict["公司名稱"] = (
        field_correct["公司名稱"] / field_total["公司名稱"] if field_total["公司名稱"] else 0
    )
    phone_precision = phone_precision_sum / phone_count if phone_count else 0.0
    phone_recall    = phone_recall_sum / phone_count    if phone_count else 0.0
    field_accuracy_dict["聯絡電話 (precision)"] = phone_precision
    field_accuracy_dict["聯絡電話 (recall)"]    = phone_recall
    field_accuracy_dict["公司地址"] = (
        field_correct["公司地址"] / field_total["公司地址"] if field_total["公司地址"] else 0
    )

    # 電話 precision/recall -> 不是 accuracy, 直接算平均
    #   圖片裡是 "聯絡電話 (precision)", "聯絡電話 (recall)"
    #   phone_precision_sum / phone_count
    #   phone_recall_sum / phone_count
    

    # 職位名稱、工作地點、工作開始時間、工作結束時間、薪資下限、薪資上限、薪資方式
    field_accuracy_dict["職位名稱"] = (
        field_correct["職位名稱"] / field_total["職位名稱"] if field_total["職位名稱"] else 0
    )
    field_accuracy_dict["工作地點"] = (
        field_correct["工作地點"] / field_total["工作地點"] if field_total["工作地點"] else 0
    )
    field_accuracy_dict["工作開始時間"] = (
        field_correct["工作開始時間"] / field_total["工作開始時間"] if field_total["工作開始時間"] else 0
    )
    field_accuracy_dict["工作結束時間"] = (
        field_correct["工作結束時間"] / field_total["工作結束時間"] if field_total["工作結束時間"] else 0
    )
    field_accuracy_dict["薪資下限"] = (
        field_correct["薪資下限"] / field_total["薪資下限"] if field_total["薪資下限"] else 0
    )
    field_accuracy_dict["薪資上限"] = (
        field_correct["薪資上限"] / field_total["薪資上限"] if field_total["薪資上限"] else 0
    )
    field_accuracy_dict["薪資方式"] = (
        field_correct["薪資方式"] / field_total["薪資方式"] if field_total["薪資方式"] else 0
    )

    # ---------------------------------------------------------------------
    # (2) top_level_accuracy = 頂層 (公司名稱,公司地址) 的正確率
    top_level_accuracy = (
        top_level_correct / top_level_total if top_level_total else 0.0
    )

    # (3) job_level_accuracy = 職位欄位的正確率 (不含電話)
    job_level_accuracy = (
        job_level_correct / job_level_total if job_level_total else 0.0
    )

    # (4) overall_accuracy = (頂層 + 職位) / (頂層total + 職位total)
    #   (不包含電話在內)
    overall_correct = top_level_correct + job_level_correct
    overall_total   = top_level_total   + job_level_total
    overall_accuracy = overall_correct / overall_total if overall_total else 0.0

    # 組出最終要印出的結構
    field_accuracy_dict = {
        key: format_float(value)
        for key, value in field_accuracy_dict.items()
    }
    top_level_accuracy = format_float(top_level_accuracy)
    job_level_accuracy = format_float(job_level_accuracy)
    overall_accuracy = format_float(overall_accuracy)

    result = {
        "field_accuracy": field_accuracy_dict,
        "top_level_accuracy": top_level_accuracy,
        "job_level_accuracy": job_level_accuracy,
        "overall_accuracy": overall_accuracy
    }
    return result

#############################
# (C) 讀取 CSV 並執行評分
#############################

def read_csv_and_calculate_metrics(csv_path):
    all_predictions = []
    all_labels = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pred_str = row["prediction"]
            gt_str   = row["ground_truth"]

            pred = parse_json_with_double_quotes_fix(pred_str)
            gt   = parse_json_with_double_quotes_fix(gt_str)

            # 若最外層是 list，拿第 1 筆
            if isinstance(pred, list) and pred:
                pred = pred[0]
            if isinstance(gt, list) and gt:
                gt = gt[0]

            all_predictions.append(pred)
            all_labels.append(gt)

    # 做後續的 evaluate_predictions
    result = evaluate_predictions(all_predictions, all_labels)
    return result


#############################
# (D) 主程式 (示範)
#############################
if __name__ == "__main__":
    # 這裡改成您實際的 CSV 路徑
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv_file_path", type=str)

    #csv_file_path = r"/home/ai/donut/result/900/3e5_800/output.csv"
    args = parser.parse_args()

    # 計算
    final_result = read_csv_and_calculate_metrics(args.csv_file_path)

    # 印出結果 - 與您圖片中的格式完全一致 (field_accuracy + 三個accuracy)
    print("=== 評估結果 ===")
    print(json.dumps(final_result, ensure_ascii=False, indent=2))
