# -*- coding: utf-8 -*-
"""扫描取数 SQL 中的日期字面量，为 skill SQL 模板占位符化做准备"""
import io, sys, re, glob, collections, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='gbk', errors='replace')
BASE = r"c:\Users\Cupshe\Desktop\test\out\ops_20261021"

pat_q = re.compile(r"'\d{4}-\d{2}-\d{2}'")    # 'YYYY-MM-DD'
pat_nq = re.compile(r"\b20\d{6}\b")           # YYYYMMDD 裸数字（pt 分区）

for f in sorted(glob.glob(os.path.join(BASE, "*.sql"))):
    src = io.open(f, encoding="utf-8").read()
    q = collections.Counter(pat_q.findall(src))
    nq = collections.Counter(pat_nq.findall(src))
    print(os.path.basename(f), "|", len(src), "chars")
    print("   quoted:", dict(q))
    print("   bare  :", dict(nq))
