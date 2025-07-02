# LawComparator 法条对比器

主要由Cursor开发的中国法律修订版本比较器。方便对比复制来的不太标准的格式的法条。 使用方法大致为: 
1. 先使用 `law_comparator.py` 对两个版本的纯文本发条进行初步对比，得到json数据与html报告
2. 对其中没有匹配到的或者匹配错误的使用 `manual_matcher.html` 加载 json文件 进行手工匹配并得到`manual_matches.json`
3. 再次进行比较，并传入手动匹配结果，得到最终的html报告

eg: 
```bash
# 1. 初步比较
python law_comparator.py ./examples/中华人民共和国反不正当竞争法_2019VS2025/中华人民共和国反不正当竞争法2019.txt ./examples/中华人民共和国反不正当竞争法_2019VS2025/中华人民共和国反不正当竞争法2025.txt
# 2. 利用 manual_matcher.html 手工匹配
# 3. 得到最终的 .html报告
python law_comparator.py ./examples/中华人民共和国反不正当竞争法_2019VS2025/中华人民共和国反不正当竞争法2019.txt ./examples/中华人民共和国反不正当竞争法_2019VS2025/中华人民共和国反不正当竞争法2025.txt -m ./examples/中华人民共和国反不正当竞争法_2019VS2025/manual_matches.json
```

在examples中可以找到三次对比的样例