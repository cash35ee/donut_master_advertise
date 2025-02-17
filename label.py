import os
import pandas as pd
import json
import shutil

# 載入 CSV 檔案
csv_path = r"C:\...\標註結果1220.csv"  # 替換為您的 CSV 檔案路徑
image_folder = r"C\...\final_database_photos"  # 替換為圖片所在資料夾的路徑
output_folder = "output1000_images"  # 替換為輸出圖片的資料夾路徑
output_jsonl = "output1000.jsonl"  # 替換成輸出的 JSONL 檔案路徑

# 創建輸出資料夾
os.makedirs(output_folder, exist_ok=True)

# 讀取 CSV
try:
    csv_data = pd.read_csv(csv_path)
    print(f"成功讀取 CSV 檔案，總共 {len(csv_data)} 行。")
except Exception as e:
    print(f"讀取 CSV 檔案時發生錯誤: {e}")
    exit(1)

# 檢查必要欄位
required_columns = ["file_name", "result"]
for col in required_columns:
    if col not in csv_data.columns:
        print(f"CSV 文件中缺少 '{col}' 欄位。請確認 CSV 格式正確。")
        exit(1)

# 將 file_name 去除前後空白並確保為字串
csv_data["file_name"] = csv_data["file_name"].astype(str).str.strip()
print("已去除 'file_name' 欄位的前後空白。")

# 初始化變數
start_index = 1  # 改名起始數字
missing_files = []  # 紀錄找不到的檔案

#搜索所有 .jpg 圖片的完整路徑
all_images = {}
for root, _, files in os.walk(image_folder):
    for file in files:
        if file.lower().endswith('.jpg'):  # 僅處理 .jpg 檔案，忽略大小寫
            all_images[file.lower()] = os.path.join(root, file)

print(f"總共找到 {len(all_images)} 張 .jpg 圖片。")
# 顯示部分圖片檔名以確認
print("示例圖片檔名及路徑：")
for i, (k, v) in enumerate(all_images.items()):
    if i >= 5:
        break
    print(f"  {k}: {v}")

# 開啟 JSONL 檔案寫入

with open(output_jsonl, "w", encoding="utf-8") as jsonl_file:
    for idx, row in csv_data.iterrows():
        original_file_name = row["file_name"]
        result = row["result"]

        # 嘗試不加 .jpg 和加 .jpg 的情況
        file_name_lower = original_file_name.lower()
        image_path = all_images.get(file_name_lower)  # 不加 .jpg
        if not image_path:
            file_name_with_jpg = f"{file_name_lower}.jpg"
            image_path = all_images.get(file_name_with_jpg)  # 加 .jpg

        if not image_path:
            # 增加偵錯輸出
            print(f"未找到圖片: 原始檔名='{original_file_name}', 嘗試檔名='{original_file_name}' 或 '{original_file_name}.jpg'")
            missing_files.append(original_file_name)
            continue

        # 生成新檔名
        new_file_name = f"advertise_{start_index:06d}.jpg"
        new_image_path = os.path.join(output_folder, new_file_name)

        try:
            # 複製圖片到新的路徑
            shutil.copy(image_path, new_image_path)
        except Exception as e:
            print(f"無法複製檔案 {image_path} 到 {new_image_path}: {e}")
            missing_files.append(original_file_name)
            continue

        # 生成 JSONL 條目
        try:
            # 將 result 字串轉換為字典
            # 假設 result 已經是有效的 JSON 字串
            # 如果 result 是雙引號包圍的字串，先將其轉為有效 JSON
            # 例如: "{""公司名稱"": ""龍之園餐廳""}" 需要轉為 {"公司名稱": "龍之園餐廳"}
            # 這裡使用 json.loads 進行解析
            result_dict = json.loads(result)
            ground_truth_str = json.dumps({"gt_parse": result_dict}, ensure_ascii=False)
            json_entry = {
                "file_name": new_file_name,
                "ground_truth": ground_truth_str
            }
            jsonl_file.write(json.dumps(json_entry, ensure_ascii=False) + "\n")
        except json.JSONDecodeError as e:
            print(f"JSON 解析錯誤，檔案: {original_file_name}, 錯誤: {e}")
            missing_files.append(original_file_name)
            continue

        # 更新索引
        start_index += 1

        # 每處理 100 個檔案，輸出一次進度
        if (idx + 1) % 100 == 0:
            print(f"已處理 {idx + 1} 行。")

# 列出找不到的檔案
if missing_files:
    print("\n找不到以下檔案:")
    for file_name in missing_files:
        print(f"  {file_name}")
else:
    print("\n所有圖片均已處理完成。")
