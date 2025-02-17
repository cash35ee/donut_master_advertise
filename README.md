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
1.後續如果要拿額外測試集去做效能評估，可能需要製作一個test資料夾丟入advertise_1023，  
格式如advertise_1000去評估  
2.這邊兩段執行的code，如果有不同的check point，並存到不同資料夾的話，  
都需要去改指令當中的檔案位置  


## 資料集  

advertise_1000裏頭  
train : 800筆資料 (包含我自製的30筆)  
validation 與 test : 同樣的253筆資料  
  
advertise_1023裏頭  
train : 1053筆資料 (包含我自製的30筆)  
validation 與 test : 1筆 (測試是否能夠work)  

## 生成metadata.jsonl

可以執行 label.py  
我當初是設計讀取圖片的資料夾，以及讀取標註的csv  
然後直接生成一個jsonl，以及生成一個裝圖片的資料夾(也就是額外新增一批圖片在資料夾當中)  
並且會修改圖片名稱成固定形式，如:"advertise_00001"，  
好方便對齊metadata跟圖片名稱  

(1)第7、8行要調整成需要讀取的csv與圖片資料夾  
第9、10行改成輸出的圖片資料夾和輸出的jsonl  
(2)如果想修改圖片固定的名稱  
第35行，是index  
第74行，是file_name的prefix  
(3)我印象中圖片若同時有不同檔案類型，好比jpg跟png同時出現在圖片裡頭  
可能會導致讀取錯誤  
所以我這邊只先讀取jpg  
若有其他檔案類型要讀取，可以如62~65行那樣，排他法去讀取檔案類型。  

剩下有些亂亂的，是debug過後的，有些只是回報錯誤，可能沒有實質用途
但我有設置哪些圖片沒有正確轉換到會回報，我就沒主動把jsonl跟圖片的處理分開。
