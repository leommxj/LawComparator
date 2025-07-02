#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
import argparse
import os
from typing import Dict, List, Any

class LawParser:
    """法律文本解析器"""
    
    def __init__(self):
        # 章节、节、条文的正则表达式模式
        self.chapter_pattern = re.compile(r'^第[一二三四五六七八九十]+章[　\s]*(.+)', re.MULTILINE)
        self.section_pattern = re.compile(r'^第[一二三四五六七八九十]+节[　\s]*(.+)', re.MULTILINE)
        self.article_pattern = re.compile(r'^第([一二三四五六七八九十百零]+)条[　\s]*(.+)', re.MULTILINE)
        
        # 中文数字转换字典
        self.chinese_to_num = self._build_chinese_number_dict()
        
    def _build_chinese_number_dict(self) -> Dict[str, int]:
        """构建基础中文数字映射字典"""
        return {
            # 基础数字
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9,
            # 数位
            '十': 10, '百': 100, '千': 1000, '万': 10000
        }
    
    def convert_chinese_number(self, chinese_num: str) -> int:
        """将中文数字转换为阿拉伯数字"""
        if not chinese_num:
            return 0
            
        # 基础数字映射
        base_numbers = self.chinese_to_num
        
        # 特殊情况处理
        if chinese_num in base_numbers:
            return base_numbers[chinese_num]
        
        # 复杂数字解析
        return self._parse_complex_chinese_number(chinese_num, base_numbers)
    
    def _parse_complex_chinese_number(self, chinese_num: str, base_numbers: Dict[str, int]) -> int:
        """解析复杂的中文数字"""
        result = 0
        temp_num = 0  # 临时存储当前数字
        i = 0
        
        while i < len(chinese_num):
            char = chinese_num[i]
            
            # 如果是基础数字（0-9）
            if char in base_numbers and base_numbers[char] < 10:
                temp_num = base_numbers[char]
                i += 1
                
            # 如果是数位单位
            elif char in ['十', '百', '千', '万']:
                unit_value = base_numbers[char]
                
                # 特殊处理："十"在开头表示10
                if char == '十' and i == 0:
                    temp_num = 1
                
                # 如果没有前导数字，默认为1
                if temp_num == 0:
                    temp_num = 1
                
                # 计算当前数位的值
                if unit_value == 10000:  # 万
                    result += temp_num * unit_value
                    temp_num = 0
                elif unit_value >= 10:  # 十、百、千
                    result += temp_num * unit_value
                    temp_num = 0
                
                i += 1
                
            # 如果是"零"
            elif char == '零':
                # 零不参与计算，只是占位
                i += 1
                
            else:
                # 未知字符，跳过
                i += 1
        
        # 加上剩余的个位数
        result += temp_num
        
        return result if result > 0 else 0
    
    def fix_pdf_line_breaks(self, text: str) -> str:
        """修复从PDF复制产生的错误换行"""
        if not text:
            return text
        
        lines = text.split('\n')
        fixed_lines = []
        i = 0
        
        while i < len(lines):
            current_line = lines[i].strip()
            
            # 如果当前行为空，跳过
            if not current_line:
                i += 1
                continue
            
            # 检查是否需要与下一行合并
            while i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                
                # 如果下一行为空，不合并
                if not next_line:
                    break
                
                # 检查是否应该合并的条件
                should_merge = self._should_merge_lines(current_line, next_line)
                
                if should_merge:
                    # 合并行
                    current_line = current_line + next_line
                    i += 1  # 跳过已合并的行
                else:
                    break
            
            fixed_lines.append(current_line)
            i += 1
        
        return '\n'.join(fixed_lines)
    
    def _should_merge_lines(self, current_line: str, next_line: str) -> bool:
        """判断两行是否应该合并"""
        # 如果当前行以句号、分号、冒号等结束，通常不合并
        if current_line.endswith(('.', '。', ';', '；', ':', '：', '!', '！', '?', '？')):
            return False
        
        # 如果下一行以特殊标识开始，不合并
        if next_line.startswith(('(', '（', '第', '条', '章', '节')):
            return False
        
        # 如果下一行以数字加括号开始（如：(一)、（二）），不合并
        if re.match(r'^[\(（][一二三四五六七八九十百千万零\d]+[\)）]', next_line):
            return False
        
        # 如果当前行以逗号、顿号结束，通常需要合并
        if current_line.endswith((',', '，', '、')):
            return True
        
        # 如果当前行没有标点符号结尾，可能需要合并
        # 同时检查全角和半角符号
        if not re.search(r'[。，；：！？、.;:!?]$', current_line):
            return True
        
        # 默认不合并
        return False
    
    def normalize_punctuation(self, text: str) -> str:
        """
        归一化标点符号，将半角符号统一转换为全角符号
        主要处理：逗号、句号、分号、冒号、问号、感叹号、括号等
        """
        if not text:
            return text
        
        # 半角到全角的映射表
        punctuation_map = {
            ',': '，',    # 逗号
            '.': '。',    # 句号  
            ';': '；',    # 分号
            ':': '：',    # 冒号
            '?': '？',    # 问号
            '!': '！',    # 感叹号
            '(': '（',    # 左括号
            ')': '）',    # 右括号
            '[': '［',    # 左方括号
            ']': '］',    # 右方括号
            '{': '｛',    # 左花括号
            '}': '｝',    # 右花括号
            '<': '《',    # 左书名号
            '>': '》',    # 右书名号
            '«': '《',    # 法文左书名号
            '»': '》',    # 法文右书名号
            '"': '"',     # 英文双引号（统一用中文引号）
            "'": "'",     # 英文单引号（统一用中文引号）
        }
        
        # 执行替换
        normalized_text = text
        for half_width, full_width in punctuation_map.items():
            normalized_text = normalized_text.replace(half_width, full_width)
        
        # 处理特殊情况：英文双引号统一替换
        normalized_text = normalized_text.replace('"', '"')
        
        # 处理数字后的点号，如果是条文编号则保持为点号
        # 例如：1. 2. 3. 这种情况保持不变
        import re
        # 将"数字。"格式改回"数字."（用于条文编号）
        normalized_text = re.sub(r'(\d+)。(\s)', r'\1. \2', normalized_text)
        
        # 清理标点符号前后的多余空格
        normalized_text = self._clean_spaces(normalized_text)
        
        return normalized_text
    
    def _clean_spaces(self, text: str) -> str:
        """清理文本中的空格"""
        if not text:
            return text
        return re.sub(r'\s+', '', text).strip()
    
    def clean_article_content(self, content: str) -> str:
        """清理条文内容，修复PDF复制问题并保持正确的段落结构"""
        if not content:
            return content
        
        # 首先修复PDF换行问题
        content = self.fix_pdf_line_breaks(content)
        
        # 归一化标点符号
        content = self.normalize_punctuation(content)
        
        # 然后按标点符号和条款标识进行正确的分段
        lines = content.split('\n')
        processed_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检查是否是条款标识（如：(一)、（二）等）
            if re.match(r'^[\(（][一二三四五六七八九十百千万零\d]+[\)）]', line):
                processed_lines.append(line)
            else:
                # 对于普通文本，如果不是以句号等结尾，可能需要与前面合并
                if processed_lines and not processed_lines[-1].endswith(('.', '。', ';', '；', ':', '：', '!', '！', '?', '？')):
                    # 如果前一行不是条款标识，则合并
                    if not re.match(r'^[\(（][一二三四五六七八九十百千万零\d]+[\)）]', processed_lines[-1]):
                        processed_lines[-1] = processed_lines[-1] + line
                    else:
                        processed_lines.append(line)
                else:
                    processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def clean_text(self, text: str) -> str:
        """清理文本，去除多余的空白字符"""
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            cleaned_line = line.strip()
            if cleaned_line:
                cleaned_lines.append(cleaned_line)
        return '\n'.join(cleaned_lines)
    
    def extract_pure_article_content(self, article_text: str) -> str:
        """提取纯净的条文内容，去除编号部分"""
        article_number_pattern = re.compile(r'^第[一二三四五六七八九十百零]+条[　\s]*')
        pure_content = article_number_pattern.sub('', article_text)
        return pure_content.strip()
    
    def parse_chapters(self, content: str) -> Dict[int, Dict[str, Any]]:
        """解析章节信息"""
        chapters = {}
        for match in self.chapter_pattern.finditer(content):
            chapter_text = match.group(0).strip()
            chapter_title = self._clean_spaces(match.group(1).strip())
            chapter_num_match = re.search(r'第([一二三四五六七八九十]+)章', chapter_text)
            if chapter_num_match:
                chapter_num = self.convert_chinese_number(chapter_num_match.group(1))
                chapters[chapter_num] = {
                    'title': chapter_title,
                    'full_text': chapter_text,
                    'sections': {}
                }
        return chapters
    
    def parse_sections(self, content: str) -> Dict[int, Dict[str, Any]]:
        """解析节信息"""
        sections = {}
        for match in self.section_pattern.finditer(content):
            section_text = match.group(0).strip()
            section_title = match.group(1).strip()
            section_num_match = re.search(r'第([一二三四五六七八九十]+)节', section_text)
            if section_num_match:
                section_num = self.convert_chinese_number(section_num_match.group(1))
                sections[section_num] = {
                    'title': section_title,
                    'full_text': section_text
                }
        return sections
    
    def parse_articles(self, content: str) -> Dict[int, Dict[str, Any]]:
        """解析条文信息，并记录每个条文所属的章节"""
        articles = {}
        content_lines = content.split('\n')
        current_article_num = None
        current_article_content = []
        
        # 跟踪当前章节信息
        current_chapter_num = None
        current_chapter_title = None
        current_section_num = None
        current_section_title = None
        
        for line in content_lines:
            line_stripped = line.strip()
            
            # 检查是否是章标题
            chapter_match = self.chapter_pattern.match(line)
            if chapter_match:
                chapter_title = chapter_match.group(1).strip()
                chapter_num_match = re.search(r'第([一二三四五六七八九十]+)章', line)
                if chapter_num_match:
                    current_chapter_num = self.convert_chinese_number(chapter_num_match.group(1))
                    current_chapter_title = chapter_title
                    # 进入新章时重置节信息
                    current_section_num = None
                    current_section_title = None
                continue
            
            # 检查是否是节标题
            section_match = self.section_pattern.match(line)
            if section_match:
                section_title = section_match.group(1).strip()
                section_num_match = re.search(r'第([一二三四五六七八九十]+)节', line)
                if section_num_match:
                    current_section_num = self.convert_chinese_number(section_num_match.group(1))
                    current_section_title = section_title
                continue
            
            # 检查是否是条文编号行
            article_match = self.article_pattern.match(line)
            if article_match:
                # 保存前一条
                if current_article_num is not None:
                    # 合并完整内容
                    full_content = '\n'.join(current_article_content).strip()
                    # 提取纯净内容（去除编号）
                    pure_content = self.extract_pure_article_content(full_content)
                    # 清理PDF换行问题
                    pure_content = self.clean_article_content(pure_content)
                    
                    articles[current_article_num] = {
                        'content': pure_content,
                        'full_text': full_content,
                        'chapter_num': current_chapter_num,
                        #'chapter_title': current_chapter_title,
                        'section_num': current_section_num,
                        #'section_title': current_section_title,
                        'line_count': len(current_article_content)
                    }
                
                # 开始新条
                current_article_num = self.convert_chinese_number(article_match.group(1))
                current_article_content = [line_stripped]
            elif current_article_num is not None and line_stripped:
                # 检查是否是章节标题，如果是则跳过
                if self._is_section_or_chapter_title(line_stripped):
                    continue
                
                # 继续当前条的内容
                current_article_content.append(line_stripped)
        
        # 保存最后一条
        if current_article_num is not None:
            # 合并完整内容
            full_content = '\n'.join(current_article_content).strip()
            # 提取纯净内容（去除编号）
            pure_content = self.extract_pure_article_content(full_content)
            # 清理PDF换行问题
            pure_content = self.clean_article_content(pure_content)
            
            articles[current_article_num] = {
                'content': pure_content,
                'full_text': full_content,
                'chapter_num': current_chapter_num,
                'chapter_title': current_chapter_title,
                'section_num': current_section_num,
                'section_title': current_section_title,
                'line_count': len(current_article_content)
            }
        
        return articles
    
    def _is_section_or_chapter_title(self, line: str) -> bool:
        """检查是否是章节标题"""
        # 检查章标题模式：第X章 标题
        if re.match(r'^第[一二三四五六七八九十]+章\s*', line):
            return True
        
        # 检查节标题模式：第X节 标题 或 第X节标题
        if re.match(r'^第[一二三四五六七八九十]+节', line):
            return True
        
        return False
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """解析法律文本文件，返回结构化数据"""
        print(f"正在解析文件: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"文件未找到: {file_path}")
        except UnicodeDecodeError:
            raise UnicodeDecodeError(f"文件编码错误，请确保文件为UTF-8编码: {file_path}")
        
        # 清理文本
        content = self.clean_text(content)
        
        # 解析各部分
        chapters = self.parse_chapters(content)
        sections = self.parse_sections(content)
        articles = self.parse_articles(content)
        
        # 构建法律结构
        law_structure = {
            'file_path': file_path,
            'chapters': chapters,
            'sections': sections,
            'articles': articles,
            'metadata': {
                'total_chapters': len(chapters),
                'total_sections': len(sections),
                'total_articles': len(articles),
                'total_content_length': len(content)
            }
        }
        
        print(f"解析完成: {len(articles)} 条法律条文, {len(chapters)} 个章节")
        return law_structure
    
    def save_parsed_data(self, law_structure: Dict[str, Any], output_file: str):
        """保存解析后的结构化数据到JSON文件"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(law_structure, f, ensure_ascii=False, indent=2)
            print(f"解析数据已保存到: {output_file}")
        except Exception as e:
            print(f"保存解析数据时出错: {e}")

def main():
    """主函数，支持命令行参数"""
    parser = argparse.ArgumentParser(
        description='法律文本解析器 - 将法律条文文本解析为结构化数据',
        epilog='使用示例: python law_parser.py input.txt -o output.json --preview 3 -f'
    )
    
    parser.add_argument('input_file', help='要解析的法律文本文件路径')
    parser.add_argument('-o', '--output', help='输出JSON文件路径')
    parser.add_argument('--preview', type=int, default=3, help='显示前N条法律条文的内容')
    parser.add_argument('-f', '--force', action='store_true', help='强制覆盖已存在的输出文件')
    
    args = parser.parse_args()
    
    try:
        if not os.path.exists(args.input_file):
            raise FileNotFoundError(f"输入文件不存在: {args.input_file}")
        
        # 确定输出文件路径
        if args.output:
            output_file = args.output
        else:
            base_name = os.path.splitext(os.path.basename(args.input_file))[0]
            output_file = f"parsed_{base_name}.json"
        
        # 检查输出文件是否已存在
        if os.path.exists(output_file) and not args.force:
            raise FileExistsError(f"输出文件已存在: {output_file}。使用 -f/--force 参数强制覆盖。")
        
        # 解析文件
        law_parser = LawParser()
        law_data = law_parser.parse_file(args.input_file)
        law_parser.save_parsed_data(law_data, output_file)
        
        # 显示预览
        articles = law_data['articles']
        print(f"\n前{args.preview}条内容预览：")
        print("-" * 60)
        for i, (article_num, article_info) in enumerate(sorted(articles.items())[:args.preview]):
            print(f"第{article_num}条:")
            print(f"  内容: {article_info['content'][:150]}...")
            print()
        
        print(f"解析结果已保存到: {output_file}")
        return 0
        
    except Exception as e:
        print(f"错误: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 