#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from typing import Dict, Tuple, Any, Set
from difflib import SequenceMatcher, Differ
import html
import os

class LawComparator:
    """法律条文对比器"""
    
    def __init__(self, similarity_threshold: float = 0.8):
        """
        初始化对比器
        :param similarity_threshold: 相似度阈值，用于判断条文是否相同
        """
        self.similarity_threshold = similarity_threshold
        self.manual_matches = []  # 存储手动匹配结果
        
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度"""
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1, text2).ratio()
    
    def find_best_match(self, target_article: Dict[str, Any], candidate_articles: Dict[int, Dict[str, Any]], 
                       used_articles: Set[int]) -> Tuple[int, float]:
        """
        为目标条文在候选条文中找到最佳匹配
        :param target_article: 目标条文
        :param candidate_articles: 候选条文字典
        :param used_articles: 已使用的条文编号集合
        :return: (最佳匹配的条文编号, 相似度)
        """
        target_content = target_article.get('content', '')
        best_match_num = -1
        best_similarity = 0.0
        
        for article_num, article_info in candidate_articles.items():
            if article_num in used_articles:
                continue
                
            candidate_content = article_info.get('content', '')
            similarity = self.calculate_similarity(target_content, candidate_content)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match_num = article_num
        
        return best_match_num, best_similarity
    
    def intelligent_article_matching(self, articles1: Dict[int, Dict[str, Any]], 
                                   articles2: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        """
        智能条文匹配算法（支持手动匹配优先）
        优先使用手动匹配结果，然后基于内容相似度进行匹配
        """
        print("正在执行智能条文匹配...")
        
        # 匹配结果
        matches = []  # [(article1_num, article2_num, similarity, match_type)]
        used_articles1 = set()  # 已匹配的第一版本条文
        used_articles2 = set()  # 已匹配的第二版本条文
        
        # 第0阶段：处理手动匹配结果
        manual_matches_processed = 0
        if self.manual_matches:
            print(f"优先处理 {len(self.manual_matches)} 个手动匹配关系...")
            
            for match in self.manual_matches:
                old_num = int(match['old_number'])
                new_num = int(match['new_number'])
                
                # 检查条文是否存在
                if old_num in articles1 and new_num in articles2:
                    # 计算相似度
                    similarity = self.calculate_similarity(
                        articles1[old_num].get('content', ''),
                        articles2[new_num].get('content', '')
                    )
                    
                    matches.append((old_num, new_num, similarity, 'manual'))
                    used_articles1.add(old_num)
                    used_articles2.add(new_num)
                    manual_matches_processed += 1
                    print(f"  手动匹配：第{old_num}条 → 第{new_num}条 (相似度: {similarity:.3f})")
                else:
                    print(f"  警告：手动匹配中的条文不存在 - 第{old_num}条 或 第{new_num}条")
            
            print(f"手动匹配处理完成，成功处理 {manual_matches_processed} 个匹配关系")
        
        # 第一阶段：为剩余版本1中的每个条文找到版本2中的最佳匹配
        remaining_articles1 = {k: v for k, v in articles1.items() if k not in used_articles1}
        remaining_articles2 = {k: v for k, v in articles2.items() if k not in used_articles2}
        
        print(f"智能匹配剩余条文：{len(remaining_articles1)} 个原条文，{len(remaining_articles2)} 个新条文")
        
        for article1_num in sorted(remaining_articles1.keys()):
            article1_info = remaining_articles1[article1_num]
            
            best_match_num, best_similarity = self.find_best_match(
                article1_info, remaining_articles2, used_articles2
            )
            
            if best_match_num != -1 and best_similarity >= self.similarity_threshold:
                matches.append((article1_num, best_match_num, best_similarity, 'auto'))
                used_articles2.add(best_match_num)
                print(f"  智能匹配：第{article1_num}条 → 第{best_match_num}条 (相似度: {best_similarity:.3f})")
            else:
                matches.append((article1_num, -1, 0.0, 'none'))  # 没有找到匹配，标记为删除
        
        # 第二阶段：处理版本2中未匹配的条文（新增条文）
        new_articles = []
        for article2_num in sorted(articles2.keys()):
            if article2_num not in used_articles2:
                new_articles.append(article2_num)
                print(f"  新增：第{article2_num}条")
        
        print(f"匹配统计：{manual_matches_processed} 个手动匹配，{len([m for m in matches if m[3] == 'auto'])} 个智能匹配")
        
        return {
            'matches': matches,
            'new': new_articles,
            'used_articles2': used_articles2,
            'manual_matches_count': manual_matches_processed
        }
    
    def compare_articles(self, law1: Dict[str, Any], law2: Dict[str, Any]) -> Dict[str, Any]:
        """比较两个法律版本的条文"""
        print("正在比较法律条文...")
        
        articles1 = law1.get('articles', {})
        articles2 = law2.get('articles', {})
        
        # 执行智能匹配
        matching_result = self.intelligent_article_matching(articles1, articles2)
        
        comparison_result = {
            'identical': [],      # 完全相同的条文
            'modified': [],       # 修改的条文
            'new': [],   # 新增的条文
            'deleted': [], # 删除的条文
            'mapping': {}         # 条文编号映射关系
        }
        
        # 统计信息
        stats = {
            'total_articles_v1': len(articles1),
            'total_articles_v2': len(articles2),
            'identical_count': 0,
            'modified_count': 0,
            'new_count': 0,
            'deleted_count': 0
        }
        
        # 处理匹配结果
        manual_count = 0
        auto_count = 0
        
        for match_data in matching_result['matches']:
            # 兼容不同的匹配结果格式
            if len(match_data) == 4:
                article1_num, article2_num, similarity, match_type = match_data
            else:
                article1_num, article2_num, similarity = match_data
                match_type = 'auto'
            
            if match_type == 'manual':
                manual_count += 1
            elif match_type == 'auto':
                auto_count += 1
            
            if article2_num == -1:
                # 删除的条文
                article1_info = articles1[article1_num]
                # 收集章节信息
                chapter_info = {
                    'chapter_num': article1_info.get('chapter_num'),
                    'chapter_title': law1.get('chapters', {}).get(article1_info.get('chapter_num'), {}).get('title', ''),
                    'section_num': article1_info.get('section_num'),
                    'section_title': law1.get('sections', {}).get(article1_info.get('section_num'), {}).get('title', '')
                }
                comparison_result['deleted'].append({
                    'article_number': article1_num,
                    'content': article1_info.get('content', ''),
                    'chapter_info': chapter_info
                })
                stats['deleted_count'] += 1
            else:
                # 建立映射关系
                comparison_result['mapping'][article1_num] = article2_num
                
                content1 = articles1[article1_num].get('content', '')
                content2 = articles2[article2_num].get('content', '')
                
                if similarity >= 0.98:  # 几乎完全相同
                    comparison_result['identical'].append({
                        'old_number': article1_num,
                        'new_number': article2_num,
                        'content': content1,
                        'similarity': similarity,
                        'match_type': match_type
                    })
                    stats['identical_count'] += 1
                else:
                    # 收集章节信息
                    old_chapter_info = {
                        'chapter_num': articles1[article1_num].get('chapter_num'),
                        'chapter_title': law1.get('chapters', {}).get(articles1[article1_num].get('chapter_num'), {}).get('title', ''),
                        'section_num': articles1[article1_num].get('section_num'),
                        'section_title': law1.get('sections', {}).get(articles1[article1_num].get('section_num'), {}).get('title', '')
                    }
                    new_chapter_info = {
                        'chapter_num': articles2[article2_num].get('chapter_num'),
                        'chapter_title': law2.get('chapters', {}).get(articles2[article2_num].get('chapter_num'), {}).get('title', ''),
                        'section_num': articles2[article2_num].get('section_num'),
                        'section_title': law2.get('sections', {}).get(articles2[article2_num].get('section_num'), {}).get('title', '')
                    }
                    
                    # 生成高亮对比HTML
                    unified_diff_html = self.generate_unified_html_diff(content1, content2)
                    
                    # 修改的条文
                    comparison_result['modified'].append({
                        'old_number': article1_num,
                        'new_number': article2_num,
                        'old_content': content1,
                        'new_content': content2,
                        'similarity': similarity,
                        'match_type': match_type,
                        'old_chapter_info': old_chapter_info,
                        'new_chapter_info': new_chapter_info,
                        'unified_diff_html': unified_diff_html
                    })
                    stats['modified_count'] += 1
        
        # 处理新增条文
        for article2_num in matching_result['new']:
            article2_info = articles2[article2_num]
            # 收集章节信息
            chapter_info = {
                'chapter_num': article2_info.get('chapter_num'),
                'chapter_title': law2.get('chapters', {}).get(article2_info.get('chapter_num'), {}).get('title', ''),
                'section_num': article2_info.get('section_num'),
                'section_title': law2.get('sections', {}).get(article2_info.get('section_num'), {}).get('title', '')
            }
            comparison_result['new'].append({
                'article_number': article2_num,
                'content': article2_info.get('content', ''),
                'chapter_info': chapter_info
            })
            stats['new_count'] += 1
        
        # 排序结果
        comparison_result['identical'].sort(key=lambda x: x['old_number'])
        comparison_result['modified'].sort(key=lambda x: x['old_number'])
        comparison_result['new'].sort(key=lambda x: x['article_number'])
        comparison_result['deleted'].sort(key=lambda x: x['article_number'])
        
        # 添加匹配方式统计
        stats['manual_matches_count'] = manual_count
        stats['auto_matches_count'] = auto_count
        
        comparison_result['statistics'] = stats
        
        print(f"智能对比完成：")
        print(f"  相同条文: {stats['identical_count']} 条")
        print(f"  修改条文: {stats['modified_count']} 条")
        print(f"  新增条文: {stats['new_count']} 条")
        print(f"  删除条文: {stats['deleted_count']} 条")
        print(f"  匹配方式: {manual_count} 个手动匹配, {auto_count} 个智能匹配")
        
        return comparison_result
    
    def generate_unified_html_diff(self, old_text: str, new_text: str) -> str:
        """
        生成统一格式的HTML对比，在同一段落中显示删除（红色背景）和新增（绿色背景）
        """
        differ = Differ()
        diff_result = list(differ.compare(old_text, new_text))
        
        html_parts = []
        
        for line in diff_result:
            if line.startswith('  '):  # 相同的部分
                content = html.escape(line[2:].strip())
                if content:
                    html_parts.append(content)
            elif line.startswith('- '):  # 删除的部分
                content = html.escape(line[2:].strip())
                if content:
                    html_parts.append(f'<span class="diff-deleted">{content}</span>')
            elif line.startswith('+ '):  # 新增的部分
                content = html.escape(line[2:].strip())
                if content:
                    html_parts.append(f'<span class="diff-added">{content}</span>')
        
        return ''.join(html_parts)
    
    def _format_chapter_info(self, old_chapter_info: Dict[str, Any] = None, new_chapter_info: Dict[str, Any] = None) -> str:
        """格式化章节信息"""
        def format_single_chapter(info):
            if not info:
                return "未知"
            
            chapter_part = f"第{info.get('chapter_num', '?')}章"
            if info.get('chapter_title'):
                chapter_part += f"《{info['chapter_title']}》"
            
            if info.get('section_num'):
                section_part = f"第{info['section_num']}节"
                if info.get('section_title'):
                    section_part += f"《{info['section_title']}》"
                return f"{chapter_part} - {section_part}"
            
            return chapter_part
        
        if old_chapter_info and new_chapter_info:
            old_formatted = format_single_chapter(old_chapter_info)
            new_formatted = format_single_chapter(new_chapter_info)
            if old_formatted == new_formatted:
                return old_formatted
            else:
                return f"{old_formatted} → {new_formatted}"
        elif old_chapter_info:
            return format_single_chapter(old_chapter_info)
        elif new_chapter_info:
            return format_single_chapter(new_chapter_info)
        else:
            return ""
    
    def save_comparison_data(self, comparison_data: Dict[str, Any], 
                           law1_info: Dict[str, Any], law2_info: Dict[str, Any],
                           output_file: str = "法律条文对比数据.json"):
        """保存对比数据到JSON文件"""
        full_comparison = {
            'metadata': {
                'law1_file': os.path.basename(law1_info.get('file_path', '未知')),
                'law2_file': os.path.basename(law2_info.get('file_path', '未知')),
            },
            'comparison_result': comparison_data,
            'law1_metadata': law1_info.get('metadata', {}),
            'law2_metadata': law2_info.get('metadata', {})
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(full_comparison, f, ensure_ascii=False, indent=2)
            print(f"对比数据已保存到: {output_file}")
        except Exception as e:
            print(f"保存对比数据时出错: {e}")
    
    def load_manual_matches(self, manual_matches_file: str) -> bool:
        """
        加载手动匹配结果
        :param manual_matches_file: 手动匹配结果JSON文件路径
        :return: 是否加载成功
        """
        try:
            with open(manual_matches_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.manual_matches = data.get('manual_matches', [])
                print(f"已加载 {len(self.manual_matches)} 个手动匹配关系")
                return True
        except FileNotFoundError:
            print(f"手动匹配文件未找到: {manual_matches_file}")
            return False
        except Exception as e:
            print(f"加载手动匹配文件时出错: {e}")
            return False
    
    def is_manually_matched(self, old_number: int = None, new_number: int = None) -> bool:
        """
        检查指定条文是否已被手动匹配
        :param old_number: 原版本条文编号
        :param new_number: 新版本条文编号
        :return: 是否已被手动匹配
        """
        for match in self.manual_matches:
            if old_number is not None and str(match['old_number']) == str(old_number):
                return True
            if new_number is not None and str(match['new_number']) == str(new_number):
                return True
        return False

    def generate_html_report(self, comparison_data: Dict[str, Any], 
                           law1_info: Dict[str, Any], law2_info: Dict[str, Any],
                           output_file: str = "法律条文对比结果.html"):
        """生成HTML格式的对比报告"""
        
        # 构建完整的比较数据
        full_comparison = {
            'metadata': {
                'law1_file': os.path.basename(law1_info.get('file_path', '未知')),
                'law2_file': os.path.basename(law2_info.get('file_path', '未知')),
            },
            'comparison_result': comparison_data
        }
        
        # HTML模板
        html_template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>法律条文对比结果</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Microsoft YaHei', 'PingFang SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 300;
        }

        .header p {
            opacity: 0.8;
            font-size: 1.1rem;
        }

        .metadata {
            background: #f8f9fa;
            padding: 20px;
            border-bottom: 1px solid #e9ecef;
        }

        .metadata-item {
            display: inline-block;
            margin-right: 30px;
            margin-bottom: 10px;
        }

        .metadata-label {
            font-weight: 600;
            color: #495057;
        }

        .stats {
            display: flex;
            justify-content: space-around;
            padding: 20px;
            background: #f1f3f4;
            border-bottom: 1px solid #e9ecef;
        }

        .stat-item {
            text-align: center;
            padding: 15px;
            border-radius: 10px;
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            min-width: 120px;
        }

        .stat-number {
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .stat-label {
            color: #6c757d;
            font-size: 0.9rem;
        }

        .identical .stat-number { color: #17a2b8; }
        .modified .stat-number { color: #ffc107; }
        .deleted .stat-number { color: #dc3545; }
        .new .stat-number { color: #28a745; }

        .filters {
            padding: 20px;
            background: white;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            gap: 15px;
            align-items: center;
        }

        .filter-button {
            padding: 8px 16px;
            border: 2px solid #dee2e6;
            background: white;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.9rem;
        }

        .filter-button.active {
            background: #007bff;
            color: white;
            border-color: #007bff;
        }

        .filter-button:hover {
            border-color: #007bff;
            transform: translateY(-2px);
        }

        .content {
            padding: 20px;
            max-height: 70vh;
            overflow-y: auto;
        }

        .section {
            margin-bottom: 30px;
        }

        .section-title {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .section-title:hover {
            transform: translateX(5px);
        }

        .section-title .toggle-icon {
            font-size: 1.2rem;
            transition: transform 0.3s ease;
        }

        .section-title.collapsed .toggle-icon {
            transform: rotate(-90deg);
        }

        .section-identical .section-title {
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            color: #0277bd;
        }

        .section-modified .section-title {
            background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%);
            color: #f57c00;
        }

        .section-deleted .section-title {
            background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
            color: #c62828;
        }

        .section-new .section-title {
            background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%);
            color: #2e7d32;
        }

        .articles-list {
            display: block;
            transition: all 0.5s ease;
        }

        .articles-list.collapsed {
            display: none;
        }

        .article-item {
            background: white;
            border: 1px solid #e9ecef;
            border-radius: 10px;
            margin-bottom: 15px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            transition: all 0.3s ease;
        }

        .article-item:hover {
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }

        /* 文本对比高亮样式 */
        .diff-deleted {
            background-color: #ffdddd;
            color: #721c24;
            padding: 2px 4px;
            border-radius: 3px;
            text-decoration: line-through;
            border: 1px solid #f5c6cb;
            margin: 0 1px;
        }

        .diff-added {
            background-color: #d4edda;
            color: #155724;
            padding: 2px 4px;
            border-radius: 3px;
            border: 1px solid #c3e6cb;
            margin: 0 1px;
        }

        /* 增强对比容器样式 */
        .diff-container {
            display: flex;
            gap: 20px;
            margin: 15px 0;
        }

        .diff-panel {
            flex: 1;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            overflow: hidden;
        }

        .diff-header {
            background: #f8f9fa;
            padding: 10px 15px;
            font-weight: 600;
            border-bottom: 1px solid #dee2e6;
            font-size: 0.9rem;
            color: #495057;
        }

        .diff-content {
            padding: 15px;
            white-space: pre-wrap;
            line-height: 1.8;
            font-size: 0.95rem;
        }


        /* 统一对比显示样式 */
        .unified-diff {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            margin: 15px 0;
            line-height: 1.8;
            font-size: 0.95rem;
        }

        .unified-diff-header {
            font-weight: 600;
            color: #495057;
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px solid #dee2e6;
        }

        /* 响应式设计 */
        @media (max-width: 768px) {
            .diff-container {
                flex-direction: column;
            }
            
            .diff-panel {
                margin-bottom: 15px;
            }
        }

        .article-header {
            padding: 15px 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .article-number {
            font-weight: 600;
            font-size: 1.1rem;
        }

        .article-meta {
            display: flex;
            gap: 15px;
            align-items: center;
        }

        .similarity-badge {
            background: #28a745;
            color: white;
            padding: 4px 8px;
            border-radius: 15px;
            font-size: 0.8rem;
        }

        .similarity-badge.medium {
            background: #ffc107;
            color: #212529;
        }

        .similarity-badge.low {
            background: #dc3545;
        }

        .chapter-info {
            font-size: 0.9rem;
            color: #6c757d;
        }

        .expand-icon {
            transition: transform 0.3s ease;
        }

        .article-header.expanded .expand-icon {
            transform: rotate(180deg);
        }

        .article-content {
            display: none;
            padding: 20px;
        }

        .article-content.expanded {
            display: block;
        }

        .diff-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }

        .diff-panel {
            border: 1px solid #e9ecef;
            border-radius: 8px;
            overflow: hidden;
        }

        .diff-header {
            padding: 10px 15px;
            font-weight: 600;
            color: white;
        }

        .diff-old .diff-header {
            background: #dc3545;
        }

        .diff-new .diff-header {
            background: #28a745;
        }

        .diff-content {
            padding: 15px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            line-height: 1.8;
            white-space: pre-wrap;
            max-height: 300px;
            overflow-y: auto;
        }

        .diff-old .diff-content {
            background: #fff5f5;
        }

        .diff-new .diff-content {
            background: #f0fff4;
        }

        .highlight-removed {
            background: #ffdddd;
            text-decoration: line-through;
            padding: 2px 4px;
            border-radius: 3px;
        }

        .highlight-added {
            background: #ddffdd;
            padding: 2px 4px;
            border-radius: 3px;
        }

        .changes-list {
            margin-top: 15px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }

        .changes-title {
            font-weight: 600;
            margin-bottom: 10px;
            color: #495057;
        }

        .change-item {
            padding: 5px 0;
            color: #6c757d;
            font-size: 0.9rem;
        }

        .identical-content {
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            line-height: 1.8;
        }

        .empty-section {
            text-align: center;
            padding: 30px;
            color: #6c757d;
            font-style: italic;
        }

        @media (max-width: 768px) {
            .diff-container {
                grid-template-columns: 1fr;
            }
            
            .stats {
                flex-direction: column;
                gap: 15px;
            }
            
            .filters {
                flex-wrap: wrap;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 法律条文对比结果</h1>
            <p>智能对比分析，支持差异展示与详细查看</p>
        </div>

        <div class="metadata" id="metadata">
            <!-- 元数据将在这里动态生成 -->
        </div>

        <div class="stats" id="stats">
            <div class="stat-item identical">
                <div class="stat-number" id="identicalCount">0</div>
                <div class="stat-label">相同条文</div>
            </div>
            <div class="stat-item modified">
                <div class="stat-number" id="modifiedCount">0</div>
                <div class="stat-label">修改条文</div>
            </div>
            <div class="stat-item deleted">
                <div class="stat-number" id="deletedCount">0</div>
                <div class="stat-label">删除条文</div>
            </div>
            <div class="stat-item new">
                <div class="stat-number" id="newCount">0</div>
                <div class="stat-label">新增条文</div>
            </div>
        </div>

        <div class="filters" id="filters">
            <span>显示类型：</span>
            <button class="filter-button active" data-filter="all">全部</button>
            <button class="filter-button" data-filter="modified">修改条文</button>
            <button class="filter-button" data-filter="identical">相同条文</button>
            <button class="filter-button" data-filter="deleted">删除条文</button>
            <button class="filter-button" data-filter="new">新增条文</button>
        </div>

        <div class="content" id="content">
            <!-- 内容将在这里动态生成 -->
        </div>
    </div>

    <script>
        // 嵌入的比较数据
        const COMPARISON_DATA = EMBEDDED_DATA_PLACEHOLDER;

        class ComparisonViewer {
            constructor() {
                this.data = COMPARISON_DATA;
                this.currentFilter = 'all';
                this.collapsedSections = new Set();
                
                // 数据验证
                if (!this.data || !this.data.comparison_result) {
                    console.error('数据格式错误:', this.data);
                    return;
                }
                
                this.init();
            }

            init() {
                try {
                    console.log('初始化比较查看器...', this.data);
                    this.setupEventListeners();
                    this.renderMetadata();
                    this.renderStats();
                    this.renderContent();
                    console.log('比较查看器初始化完成');
                } catch (error) {
                    console.error('初始化失败:', error);
                }
            }

            setupEventListeners() {
                document.querySelectorAll('.filter-button').forEach(button => {
                    button.addEventListener('click', (e) => {
                        this.setFilter(e.target.dataset.filter);
                    });
                });
            }

            setFilter(filter) {
                this.currentFilter = filter;
                
                document.querySelectorAll('.filter-button').forEach(btn => {
                    btn.classList.remove('active');
                });
                document.querySelector(`[data-filter="${filter}"]`).classList.add('active');
                
                this.renderContent();
            }

            renderMetadata() {
                const metadata = this.data.metadata;
                const metadataEl = document.getElementById('metadata');
                
                metadataEl.innerHTML = `
                    <div class="metadata-item">
                        <span class="metadata-label">原版文件：</span>
                        ${metadata.law1_file}
                    </div>
                    <div class="metadata-item">
                        <span class="metadata-label">新版文件：</span>
                        ${metadata.law2_file}
                    </div>
                `;
            }

            renderStats() {
                const result = this.data.comparison_result;
                document.getElementById('identicalCount').textContent = (result.identical || []).length;
                document.getElementById('modifiedCount').textContent = (result.modified || []).length;
                document.getElementById('deletedCount').textContent = (result.deleted || []).length;
                document.getElementById('newCount').textContent = (result.new || []).length;
            }

            renderContent() {
                const contentEl = document.getElementById('content');
                const result = this.data.comparison_result;
                
                let html = '';

                if (this.currentFilter === 'all' || this.currentFilter === 'modified') {
                    html += this.renderSection('modified', '修改的条文', result.modified || [], 'modified');
                }
                
                if (this.currentFilter === 'all' || this.currentFilter === 'identical') {
                    html += this.renderSection('identical', '相同的条文', result.identical || [], 'identical');
                }
                
                if (this.currentFilter === 'all' || this.currentFilter === 'deleted') {
                    html += this.renderSection('deleted', '删除的条文', result.deleted || [], 'deleted');
                }
                
                if (this.currentFilter === 'all' || this.currentFilter === 'new') {
                    html += this.renderSection('new', '新增的条文', result.new || [], 'new');
                }

                contentEl.innerHTML = html;
            }

            renderSection(sectionId, title, articles, type) {
                if (!articles || articles.length === 0) {
                    return `
                        <div class="section section-${type}">
                            <div class="section-title">
                                <span>${title} (0)</span>
                                <span class="toggle-icon">▼</span>
                            </div>
                            <div class="articles-list">
                                <div class="empty-section">暂无${title.replace('的条文', '')}条文</div>
                            </div>
                        </div>
                    `;
                }

                const isCollapsed = this.collapsedSections.has(sectionId);
                const articlesHtml = articles.map((article, index) => {
                    return this.renderArticle(article, type, `${sectionId}-${index}`);
                }).join('');

                return `
                    <div class="section section-${type}">
                        <div class="section-title ${isCollapsed ? 'collapsed' : ''}" 
                             onclick="window.comparisonViewer && window.comparisonViewer.toggleSection('${sectionId}')">
                            <span>${title} (${articles.length})</span>
                            <span class="toggle-icon">▼</span>
                        </div>
                        <div class="articles-list ${isCollapsed ? 'collapsed' : ''}">
                            ${articlesHtml}
                        </div>
                    </div>
                `;
            }

            renderArticle(article, type, articleId) {
                const similarity = article.similarity || 1.0;
                const similarityClass = similarity >= 0.9 ? '' : similarity >= 0.7 ? 'medium' : 'low';
                
                let headerInfo = '';
                let contentHtml = '';

                if (type === 'modified') {
                    headerInfo = `
                        <div class="article-meta">
                            <span class="similarity-badge ${similarityClass}">
                                ${Math.round(similarity * 100)}%
                            </span>
                            <span class="chapter-info">
                                第${article.old_number}条 → 第${article.new_number}条
                            </span>
                            <span class="expand-icon">▼</span>
                        </div>
                    `;
                    
                    // 原版内容和新版内容面板只显示纯文本
                    let diffContent = `
                        <div class="diff-container">
                            <div class="diff-panel diff-old">
                                <div class="diff-header">原版内容（第${article.old_number}条）</div>
                                <div class="diff-content">${this.escapeHtml(article.old_content)}</div>
                            </div>
                            <div class="diff-panel diff-new">
                                <div class="diff-header">新版内容（第${article.new_number}条）</div>
                                <div class="diff-content">${this.escapeHtml(article.new_content)}</div>
                            </div>
                        </div>
                    `;
                    
                    // 添加统一对比视图
                    let unifiedDiff = '';
                    if (article.unified_diff_html) {
                        unifiedDiff = `
                            <div class="unified-diff">
                                <div class="unified-diff-header">统一对比视图</div>
                                <div class="unified-diff-content">${article.unified_diff_html}</div>
                            </div>
                        `;
                    }
                    
                    contentHtml = `
                        ${diffContent}
                        ${unifiedDiff}
                        ${this.renderChapterInfo(article)}
                    `;
                } else if (type === 'identical') {
                    headerInfo = `
                        <div class="article-meta">
                            <span class="similarity-badge">100%</span>
                            <span class="chapter-info">
                                第${article.old_number}条 → 第${article.new_number}条
                            </span>
                            <span class="expand-icon">▼</span>
                        </div>
                    `;
                    
                    contentHtml = `
                        <div class="identical-content">${this.escapeHtml(article.content)}</div>
                    `;
                } else {
                    const number = article.article_number || article.old_number || article.new_number;
                    headerInfo = `
                        <div class="article-meta">
                            <span class="chapter-info">第${number}条</span>
                            <span class="expand-icon">▼</span>
                        </div>
                    `;
                    
                    contentHtml = `
                        <div class="identical-content">${this.escapeHtml(article.content)}</div>
                        ${this.renderChapterInfo(article)}
                    `;
                }

                const number = article.article_number || article.old_number || article.new_number;
                
                return `
                    <div class="article-item">
                        <div class="article-header" onclick="window.comparisonViewer && window.comparisonViewer.toggleArticle('${articleId}')">
                            <div class="article-number">第${number}条</div>
                            ${headerInfo}
                        </div>
                        <div class="article-content" id="content-${articleId}">
                            ${contentHtml}
                        </div>
                    </div>
                `;
            }



            renderChapterInfo(article) {
                if (!article.old_chapter_info && !article.new_chapter_info && !article.chapter_info) {
                    return '';
                }
                
                let chapterHtml = '<div class="changes-list"><div class="changes-title">📚 章节信息</div>';
                
                if (article.old_chapter_info) {
                    const oldChapter = article.old_chapter_info;
                    chapterHtml += `<div class="change-item">原版：第${oldChapter.chapter_num}章《${oldChapter.chapter_title}》</div>`;
                }
                
                if (article.new_chapter_info) {
                    const newChapter = article.new_chapter_info;
                    chapterHtml += `<div class="change-item">新版：第${newChapter.chapter_num}章《${newChapter.chapter_title}》</div>`;
                }
                
                if (article.chapter_info) {
                    const chapter = article.chapter_info;
                    chapterHtml += `<div class="change-item">章节：第${chapter.chapter_num}章《${chapter.chapter_title}》</div>`;
                }
                
                chapterHtml += '</div>';
                return chapterHtml;
            }

            toggleSection(sectionId) {
                if (this.collapsedSections.has(sectionId)) {
                    this.collapsedSections.delete(sectionId);
                } else {
                    this.collapsedSections.add(sectionId);
                }
                this.renderContent();
            }

            toggleArticle(articleId) {
                const content = document.getElementById(`content-${articleId}`);
                const header = content.previousElementSibling;
                
                if (content.classList.contains('expanded')) {
                    content.classList.remove('expanded');
                    header.classList.remove('expanded');
                } else {
                    content.classList.add('expanded');
                    header.classList.add('expanded');
                }
            }

            escapeHtml(text) {
                if (!text) return '';
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            showError(message) {
                const contentEl = document.getElementById('content');
                contentEl.innerHTML = `
                    <div style="text-align: center; padding: 50px; color: #dc3545;">
                        <h3>❌ 错误</h3>
                        <p>${message}</p>
                    </div>
                `;
            }
        }

        // 全局实例
        window.comparisonViewer = null;

        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', () => {
            window.comparisonViewer = new ComparisonViewer();
        });
    </script>
</body>
</html>'''
        
        # 将数据嵌入HTML
        data_json = json.dumps(full_comparison, ensure_ascii=False, indent=2)
        html_content = html_template.replace('EMBEDDED_DATA_PLACEHOLDER', data_json)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"HTML对比报告已保存到: {output_file}")
        except Exception as e:
            print(f"保存HTML报告时出错: {e}")

def main():
    """独立运行对比器"""
    import argparse
    from law_parser import LawParser
    
    parser = argparse.ArgumentParser(description='法律条文智能对比器')
    parser.add_argument('law1', help='第一个法律文件路径')
    parser.add_argument('law2', help='第二个法律文件路径')
    parser.add_argument('-t', '--threshold', type=float, default=0.8, help='相似度阈值 (默认: 0.8)')
    parser.add_argument('--no-html', action='store_true', help='不生成HTML报告')
    parser.add_argument('--no-json', action='store_true', help='不保存JSON数据')
    parser.add_argument('-m', '--manual-matches', help='手动匹配JSON文件路径')
    parser.add_argument('-o', '--output-prefix', default='法律条文对比', help='输出文件前缀 (默认: 法律条文对比)')
    
    args = parser.parse_args()
    
    # 初始化解析器和对比器
    law_parser = LawParser()
    comparator = LawComparator(similarity_threshold=args.threshold)
    
    # 加载手动匹配（如果提供）
    if args.manual_matches:
        comparator.load_manual_matches(args.manual_matches)
    
    try:
        print("开始解析法律文件...")
        law1_data = law_parser.parse_file(args.law1)
        law2_data = law_parser.parse_file(args.law2)
        
        print("开始法律条文智能对比...")
        
        # 执行对比
        comparison_result = comparator.compare_articles(law1_data, law2_data)
        
        # 生成报告
        generated_files = []
        
        if not args.no_html:
            html_file = f"{args.output_prefix}结果.html"
            comparator.generate_html_report(comparison_result, law1_data, law2_data, html_file)
            generated_files.append(html_file)
        
        if not args.no_json:
            json_file = f"{args.output_prefix}数据.json"
            comparator.save_comparison_data(comparison_result, law1_data, law2_data, json_file)
            generated_files.append(json_file)
        
        print(f"\n✅ 智能对比完成！生成的文件：")
        for file in generated_files:
            print(f"  • {file}")
        
    except Exception as e:
        print(f"运行时出错: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 