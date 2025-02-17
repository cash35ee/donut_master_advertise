# donut_master_advertise

## inference

inference是分兩段式去執行

第一段是依照原始paper的inference會輸出Tree Edit Distance (TED)score跟 F1 accuracy score，並且我額外寫了將output存進csv

執行 python test.py --dataset_name_or_path ./advertise_1023 --pretrained_model_name_or_path ./result/1023/8e5_800/train_cord/test_experiment --save_path ./result/1023/8e5_800/output.json
第一段執行完成大約會長這個樣子
![image](https://github.com/user-attachments/assets/798f04cf-56db-4819-8d2f-af2be484c149)


第二段是依照上一段輸出的csv去得出下游任務的Metrics，也就是欄位跟整體正確率
執行 python test_try.py --csv_file_path ./result/1023/8e5_800/output.csv
第二段執行大約會長這個樣子
![image](https://github.com/user-attachments/assets/986c94ba-0ba5-41fc-b56c-bb871b764fb0)


注意:
1.後續如果要拿額外測試集去做效能評估，可能需要製作一個test資料夾丟入advertise_1023，格式如advertise_1000去評估
2.這邊兩段執行的code，如果有不同的check point，並存到不同資料夾的話，都需要去改指令當中的檔案位置


## 資料集

advertise_1000裏頭
train : 800筆資料 (包含我自製的30筆)
validation 與 test : 同樣的253筆資料

advertise_1023裏頭
train : 1053筆資料 (包含我自製的30筆)
validation 與 test : 1筆 (測試是否能夠work)
