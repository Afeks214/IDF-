#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd

file_path = "/home/QuantNova/IDF-/קובץ בדיקות כולל לקריית התקשוב גרסא מלאה 150725 (1).xlsx"
df_main = pd.read_excel(file_path, sheet_name='טבלה מרכזת', header=3)

print("Column names in main table:")
for i, col in enumerate(df_main.columns):
    print(f"  {i}: '{col}'")
    
print(f"\nTotal columns: {len(df_main.columns)}")
print(f"Total rows: {len(df_main)}")