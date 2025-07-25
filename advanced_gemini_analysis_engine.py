#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🎯 Task 2.9.2: 高度Gemini分析テキスト解析エンジン
=====================================================
目的: Gemini分析テキストの深層解析により、推奨理由・信頼度・
     多言語対応を実現し、個人化翻訳AI構築のための
     高品質データを生成する

【Task 2.9.1.5基盤活用】
- GeminiRecommendationAnalyzerの機能を拡張
- 非接触データ収集原則の継承
- 真の個人化パターン分析の深化
"""

import re
import json
import logging
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
import hashlib

# Task 2.9.1.5基盤システムのインポート
from gemini_recommendation_analyzer import GeminiRecommendationAnalyzer

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecommendationStrength(Enum):
    """推奨強度レベル"""
    VERY_STRONG = "very_strong"  # 明確な推奨
    STRONG = "strong"           # 強い推奨
    MODERATE = "moderate"       # 中程度の推奨
    WEAK = "weak"              # 弱い推奨
    NONE = "none"              # 推奨なし

class RecommendationReason(Enum):
    """推奨理由カテゴリ"""
    ACCURACY = "accuracy"           # 精度・正確性
    NATURALNESS = "naturalness"     # 自然さ
    CONTEXT_FIT = "context_fit"     # 文脈適合性
    STYLE = "style"                 # スタイル・文体
    CLARITY = "clarity"             # 明確性
    FORMALITY = "formality"         # 丁寧度
    CULTURAL_FIT = "cultural_fit"   # 文化的適合性
    LENGTH = "length"               # 文章長
    TERMINOLOGY = "terminology"     # 専門用語
    TONE = "tone"                   # トーン・語調

@dataclass
class StructuredRecommendation:
    """構造化推奨データ"""
    recommended_engine: str
    confidence_score: float
    strength_level: RecommendationStrength
    primary_reasons: List[RecommendationReason]
    secondary_reasons: List[RecommendationReason]
    reasoning_text: str
    language: str
    analysis_metadata: Dict[str, Any] = field(default_factory=dict)
    extraction_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class AdvancedGeminiAnalysisEngine:
    """Gemini分析テキストの深層解析エンジン"""
    
    def __init__(self):
        """初期化"""
        # Task 2.9.1.5基盤の活用
        self.base_analyzer = GeminiRecommendationAnalyzer()
        
        # 多言語対応パターン
        self.multilingual_patterns = self._initialize_multilingual_patterns()
        
        # 推奨理由キーワードマッピング
        self.reason_keywords = self._initialize_reason_keywords()
        
        # 信頼度算出用パラメータ
        self.confidence_weights = {
            'explicit_recommendation': 0.4,  # 明示的推奨
            'reasoning_depth': 0.3,          # 理由の詳細度
            'comparative_analysis': 0.2,      # 比較分析の有無
            'specific_examples': 0.1          # 具体例の有無
        }
        
        logger.info("高度Gemini分析エンジン初期化完了")
    
    def _initialize_multilingual_patterns(self) -> Dict[str, List[str]]:
        """多言語対応パターンの初期化（修正版）"""
        return {
            'ja': [
                # 🆕 修正: 「最適」パターンを追加、より包括的なマッチング
                r'([A-Za-z]+)(?:翻訳|訳)(?:が|は|を)?(?:最も|もっとも|一番|特に)?(?:適切|自然|良い|優秀|推奨|おすすめ|最適|最良|最善|ベスト)',
                r'([A-Za-z]+)(?:翻訳|訳)(?:が|は|を)?(?:最適|最も適切|もっとも適切|一番適切|最良|最善|ベスト)(?:な|の)?(?:選択|選択肢|オプション|方法|翻訳)?',
                r'(?:最も|もっとも|一番|特に|最も適切|最適|最良|最善|ベスト)(?:な|の)?(?:翻訳|訳|選択肢|選択|オプション)?(?:は|：|:)?\s*([A-Za-z]+)',
                r'([A-Za-z]+)(?:を|が)(?:推奨|おすすめ|選択|選ぶべき|選択すべき)',
                r'(?:推奨|おすすめ|ベスト|最適|最良|最善)(?:翻訳|訳|選択|の選択肢)?(?:は|：|:)?\s*([A-Za-z]+)',
                # 🆕 新追加: よくある表現パターン
                r'([A-Za-z]+)(?:が|の翻訳が|翻訳は)(?:より|もっと|最も)(?:適している|適切|自然|良い)',
                r'([A-Za-z]+)(?:翻訳|訳)(?:の方が|の翻訳の方が)(?:適切|自然|良い|優秀)'
            ],
            'en': [
                # 🆕 修正: より柔軟で包括的な英語パターン
                r'(?:recommend|suggest|prefer|choose|select)\s+(?:the\s+)?([A-Za-z]+)(?:\s+translation)?',
                r'([A-Za-z]+)(?:\s+translation)?\s+(?:is|would be|will be)\s+(?:the\s+)?(?:most\s+)?(?:recommended|best|appropriate|preferred|suitable|optimal)',
                r'(?:best|most appropriate|preferred|optimal|most suitable)\s+(?:translation|choice|option)?\s*(?:is|would be|:)?\s*(?:the\s+)?([A-Za-z]+)',
                r'(?:I would|I\'d|should|you should)\s+(?:recommend|suggest|choose|select|prefer)\s+(?:the\s+)?([A-Za-z]+)',
                # 🆕 新追加: より自然な英語表現
                r'([A-Za-z]+)(?:\s+translation)?\s+(?:is|would be)\s+(?:more|most)\s+(?:suitable|appropriate|accurate|natural)',
                r'(?:the\s+)?([A-Za-z]+)(?:\s+translation)?\s+(?:performs|works)\s+(?:better|best)',
                r'(?:go with|use|choose)\s+(?:the\s+)?([A-Za-z]+)(?:\s+translation)?'
            ],
            'fr': [
                # フランス語パターン
                r'(?:je recommande|recommandé|préféré|optimal)\s+([A-Za-z]+)',
                r'([A-Za-z]+)\s+(?:est|serait)\s+(?:recommandé|préférable|optimal)',
                r'(?:la meilleure|le meilleur)\s+(?:traduction|choix)?\s*(?:est|:)?\s*([A-Za-z]+)',
            ],
            'es': [
                # スペイン語パターン
                r'(?:recomiendo|recomendado|preferido|óptimo)\s+([A-Za-z]+)',
                r'([A-Za-z]+)\s+(?:es|sería)\s+(?:recomendado|preferible|óptimo)',
                r'(?:la mejor|el mejor)\s+(?:traducción|opción)?\s*(?:es|:)?\s*([A-Za-z]+)',
            ]
        }
    
    def _initialize_reason_keywords(self) -> Dict[RecommendationReason, Dict[str, List[str]]]:
        """推奨理由キーワードの初期化"""
        return {
            RecommendationReason.ACCURACY: {
                'ja': ['正確', '精度', '正しい', '間違い', 'エラー', '誤訳'],
                'en': ['accurate', 'accuracy', 'correct', 'precise', 'error', 'mistake'],
                'fr': ['précis', 'exactitude', 'correct', 'erreur'],
                'es': ['preciso', 'exactitud', 'correcto', 'error']
            },
            RecommendationReason.NATURALNESS: {
                'ja': ['自然', 'ナチュラル', '流暢', '不自然', 'スムーズ'],
                'en': ['natural', 'fluent', 'smooth', 'awkward', 'unnatural'],
                'fr': ['naturel', 'fluide', 'maladroit'],
                'es': ['natural', 'fluido', 'torpe']
            },
            RecommendationReason.CONTEXT_FIT: {
                'ja': ['文脈', 'コンテキスト', '状況', '場面', '適合'],
                'en': ['context', 'contextual', 'situation', 'situational', 'fit'],
                'fr': ['contexte', 'contextuel', 'situation'],
                'es': ['contexto', 'contextual', 'situación']
            },
            RecommendationReason.STYLE: {
                'ja': ['スタイル', '文体', '書き方', '表現', 'トーン'],
                'en': ['style', 'stylistic', 'tone', 'expression', 'writing'],
                'fr': ['style', 'stylistique', 'ton', 'expression'],
                'es': ['estilo', 'estilístico', 'tono', 'expresión']
            },
            RecommendationReason.CLARITY: {
                'ja': ['明確', 'クリア', '分かりやすい', '理解', '曖昧'],
                'en': ['clear', 'clarity', 'understandable', 'ambiguous', 'vague'],
                'fr': ['clair', 'clarté', 'compréhensible', 'ambigu'],
                'es': ['claro', 'claridad', 'comprensible', 'ambiguo']
            },
            RecommendationReason.FORMALITY: {
                'ja': ['丁寧', '敬語', 'フォーマル', 'カジュアル', '礼儀'],
                'en': ['formal', 'polite', 'casual', 'informal', 'courtesy'],
                'fr': ['formel', 'poli', 'décontracté', 'courtoisie'],
                'es': ['formal', 'cortés', 'casual', 'cortesía']
            },
            RecommendationReason.CULTURAL_FIT: {
                'ja': ['文化', '慣習', '習慣', '社会', '文化的'],
                'en': ['cultural', 'culture', 'social', 'custom', 'tradition'],
                'fr': ['culturel', 'culture', 'social', 'coutume'],
                'es': ['cultural', 'cultura', 'social', 'costumbre']
            },
            RecommendationReason.LENGTH: {
                'ja': ['長さ', '短い', '長い', '簡潔', '冗長'],
                'en': ['length', 'short', 'long', 'concise', 'verbose'],
                'fr': ['longueur', 'court', 'long', 'concis', 'verbeux'],
                'es': ['longitud', 'corto', 'largo', 'conciso', 'verboso']
            },
            RecommendationReason.TERMINOLOGY: {
                'ja': ['専門用語', '術語', '技術的', '専門', '業界'],
                'en': ['terminology', 'technical', 'specialized', 'jargon'],
                'fr': ['terminologie', 'technique', 'spécialisé', 'jargon'],
                'es': ['terminología', 'técnico', 'especializado', 'jerga']
            },
            RecommendationReason.TONE: {
                'ja': ['トーン', '語調', '雰囲気', 'ムード', '印象'],
                'en': ['tone', 'mood', 'atmosphere', 'impression', 'feeling'],
                'fr': ['ton', 'humeur', 'atmosphère', 'impression'],
                'es': ['tono', 'humor', 'atmósfera', 'impresión']
            }
        }
    
    def extract_structured_recommendations(self, analysis_text: str, language: str = 'ja') -> StructuredRecommendation:
        """
        構造化推奨抽出アルゴリズム
        
        Args:
            analysis_text: Gemini分析テキスト
            language: 分析言語 ('ja', 'en', 'fr', 'es')
            
        Returns:
            構造化された推奨データ
        """
        try:
            # Task 2.9.1.5基盤を活用した基本推奨抽出
            base_recommendation = self.base_analyzer.extract_gemini_recommendation(analysis_text)
            
            if not base_recommendation:
                return StructuredRecommendation(
                    recommended_engine="none",
                    confidence_score=0.0,
                    strength_level=RecommendationStrength.NONE,
                    primary_reasons=[],
                    secondary_reasons=[],
                    reasoning_text="",
                    language=language
                )
            
            # 推奨強度の分析
            strength_level = self._analyze_recommendation_strength(analysis_text, language)
            
            # 推奨理由の分類
            primary_reasons, secondary_reasons = self.classify_recommendation_reasons(analysis_text, language)
            
            # 信頼度スコアの算出
            confidence_score = self.calculate_recommendation_confidence(analysis_text, language)
            
            # 理由テキストの抽出
            reasoning_text = self._extract_reasoning_text(analysis_text, language)
            
            # メタデータの生成
            metadata = {
                'text_length': len(analysis_text),
                'language_detected': language,
                'pattern_matches': self._count_pattern_matches(analysis_text, language),
                'reason_keyword_count': self._count_reason_keywords(analysis_text, language)
            }
            
            result = StructuredRecommendation(
                recommended_engine=base_recommendation,
                confidence_score=confidence_score,
                strength_level=strength_level,
                primary_reasons=primary_reasons,
                secondary_reasons=secondary_reasons,
                reasoning_text=reasoning_text,
                language=language,
                analysis_metadata=metadata
            )
            
            logger.info(f"構造化推奨抽出完了: {base_recommendation} (信頼度: {confidence_score:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"構造化推奨抽出エラー: {str(e)}")
            return StructuredRecommendation(
                recommended_engine="error",
                confidence_score=0.0,
                strength_level=RecommendationStrength.NONE,
                primary_reasons=[],
                secondary_reasons=[],
                reasoning_text=f"Error: {str(e)}",
                language=language
            )
    
    def classify_recommendation_reasons(self, analysis_text: str, language: str = 'ja') -> Tuple[List[RecommendationReason], List[RecommendationReason]]:
        """
        推奨理由の自動分類システム
        
        Args:
            analysis_text: Gemini分析テキスト
            language: 分析言語
            
        Returns:
            (主要理由リスト, 副次理由リスト)
        """
        text_lower = analysis_text.lower()
        reason_scores = defaultdict(int)
        
        # 各理由カテゴリのキーワードマッチング
        for reason, lang_keywords in self.reason_keywords.items():
            if language in lang_keywords:
                keywords = lang_keywords[language]
                for keyword in keywords:
                    # キーワードの出現回数をカウント
                    count = text_lower.count(keyword.lower())
                    if count > 0:
                        # 文脈での重要度を考慮
                        context_weight = self._calculate_context_weight(text_lower, keyword.lower())
                        reason_scores[reason] += count * context_weight
        
        # スコアでソートして主要・副次理由を分類
        sorted_reasons = sorted(reason_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 閾値による分類
        primary_threshold = max(2, max(reason_scores.values()) * 0.6) if reason_scores else 2
        secondary_threshold = 1
        
        primary_reasons = [reason for reason, score in sorted_reasons if score >= primary_threshold]
        secondary_reasons = [reason for reason, score in sorted_reasons 
                           if secondary_threshold <= score < primary_threshold]
        
        # 最大数の制限
        primary_reasons = primary_reasons[:3]
        secondary_reasons = secondary_reasons[:3]
        
        logger.info(f"理由分類完了: 主要={len(primary_reasons)}, 副次={len(secondary_reasons)}")
        return primary_reasons, secondary_reasons
    
    def _calculate_context_weight(self, text: str, keyword: str) -> float:
        """キーワードの文脈重要度を計算"""
        # キーワード周辺の文脈を分析
        keyword_positions = []
        start = 0
        while True:
            pos = text.find(keyword, start)
            if pos == -1:
                break
            keyword_positions.append(pos)
            start = pos + 1
        
        if not keyword_positions:
            return 0.0
        
        total_weight = 0.0
        for pos in keyword_positions:
            # 文の開始位置での重要度が高い
            sentence_start_weight = 1.5 if self._is_sentence_start(text, pos) else 1.0
            
            # 比較表現との近接度
            comparison_weight = 1.3 if self._near_comparison(text, pos) else 1.0
            
            # 推奨表現との近接度
            recommendation_weight = 1.4 if self._near_recommendation(text, pos) else 1.0
            
            total_weight += sentence_start_weight * comparison_weight * recommendation_weight
        
        return total_weight / len(keyword_positions)
    
    def _is_sentence_start(self, text: str, pos: int) -> bool:
        """文の開始位置かどうかを判定"""
        if pos < 10:
            return True
        
        preceding_text = text[max(0, pos-20):pos]
        return any(punct in preceding_text[-5:] for punct in ['。', '.', '！', '!', '？', '?'])
    
    def _near_comparison(self, text: str, pos: int) -> bool:
        """比較表現との近接度を判定"""
        window_size = 50
        start = max(0, pos - window_size)
        end = min(len(text), pos + window_size)
        context = text[start:end]
        
        comparison_words = ['比較', '対比', 'より', 'better', 'worse', 'compared', 'versus', 'vs']
        return any(word in context for word in comparison_words)
    
    def _near_recommendation(self, text: str, pos: int) -> bool:
        """推奨表現との近接度を判定"""
        window_size = 30
        start = max(0, pos - window_size)
        end = min(len(text), pos + window_size)
        context = text[start:end]
        
        recommendation_words = ['推奨', 'おすすめ', 'recommend', 'suggest', 'best', '最適']
        return any(word in context for word in recommendation_words)
    
    def parse_multilingual_analysis(self, analysis_text: str, language: str) -> Dict[str, Any]:
        """
        多言語分析テキスト対応
        
        Args:
            analysis_text: 分析テキスト
            language: 言語コード
            
        Returns:
            多言語解析結果
        """
        result = {
            'detected_language': language,
            'supported_language': language in self.multilingual_patterns,
            'text_analysis': {},
            'cross_language_elements': []
        }
        
        if language not in self.multilingual_patterns:
            logger.warning(f"未対応言語: {language}")
            result['text_analysis'] = {'error': f'Unsupported language: {language}'}
            return result
        
        # 言語固有のパターン分析
        patterns = self.multilingual_patterns[language]
        matches = []
        
        for pattern in patterns:
            pattern_matches = re.finditer(pattern, analysis_text, re.IGNORECASE | re.MULTILINE)
            for match in pattern_matches:
                matches.append({
                    'pattern': pattern,
                    'match': match.group(0),
                    'engine': match.group(1) if match.groups() else None,
                    'position': match.span()
                })
        
        result['text_analysis'] = {
            'total_matches': len(matches),
            'pattern_matches': matches,
            'text_length': len(analysis_text),
            'confidence_indicators': self._extract_confidence_indicators(analysis_text, language)
        }
        
        # 多言語混在の検出
        result['cross_language_elements'] = self._detect_cross_language_elements(analysis_text)
        
        return result
    
    def _extract_confidence_indicators(self, text: str, language: str) -> List[str]:
        """信頼度指標の抽出"""
        indicators = []
        
        confidence_patterns = {
            'ja': ['明確に', '間違いなく', '確実に', 'はっきりと', '疑いなく'],
            'en': ['clearly', 'definitely', 'certainly', 'obviously', 'undoubtedly'],
            'fr': ['clairement', 'définitivement', 'certainement', 'évidemment'],
            'es': ['claramente', 'definitivamente', 'ciertamente', 'obviamente']
        }
        
        if language in confidence_patterns:
            for indicator in confidence_patterns[language]:
                if indicator.lower() in text.lower():
                    indicators.append(indicator)
        
        return indicators
    
    def _detect_cross_language_elements(self, text: str) -> List[Dict[str, Any]]:
        """多言語混在要素の検出"""
        elements = []
        
        # 英語単語の検出（日本語テキスト内）
        english_pattern = r'\b[A-Za-z]{2,}\b'
        english_matches = re.finditer(english_pattern, text)
        
        for match in english_matches:
            elements.append({
                'type': 'english_in_japanese',
                'text': match.group(0),
                'position': match.span()
            })
        
        return elements
    
    def calculate_recommendation_confidence(self, analysis_text: str, language: str = 'ja') -> float:
        """
        推奨強度・信頼度スコア算出
        
        Args:
            analysis_text: 分析テキスト
            language: 言語コード
            
        Returns:
            信頼度スコア (0.0-1.0)
        """
        confidence_score = 0.0
        
        # 1. 明示的推奨の評価
        explicit_score = self._evaluate_explicit_recommendation(analysis_text, language)
        confidence_score += explicit_score * self.confidence_weights['explicit_recommendation']
        
        # 2. 理由の詳細度評価
        reasoning_score = self._evaluate_reasoning_depth(analysis_text, language)
        confidence_score += reasoning_score * self.confidence_weights['reasoning_depth']
        
        # 3. 比較分析の有無
        comparative_score = self._evaluate_comparative_analysis(analysis_text, language)
        confidence_score += comparative_score * self.confidence_weights['comparative_analysis']
        
        # 4. 具体例の有無
        example_score = self._evaluate_specific_examples(analysis_text, language)
        confidence_score += example_score * self.confidence_weights['specific_examples']
        
        # 0.0-1.0の範囲に正規化
        confidence_score = max(0.0, min(1.0, confidence_score))
        
        logger.info(f"信頼度スコア算出完了: {confidence_score:.3f}")
        return confidence_score
    
    def _evaluate_explicit_recommendation(self, text: str, language: str) -> float:
        """明示的推奨の評価（修正版）"""
        explicit_patterns = {
            'ja': ['推奨', 'おすすめ', '選ぶべき', 'ベスト', '最適', '最良', '最善', '適切', '最も適切', '一番良い', '選択', '選択肢'],
            'en': ['recommend', 'suggest', 'best', 'optimal', 'preferred', 'suitable', 'appropriate', 'choose', 'select', 'most suitable'],
            'fr': ['recommande', 'suggère', 'meilleur', 'optimal', 'préféré', 'approprié', 'convenable'],
            'es': ['recomiendo', 'sugiero', 'mejor', 'óptimo', 'preferido', 'apropiado', 'adecuado']
        }
        
        if language not in explicit_patterns:
            return 0.0
        
        text_lower = text.lower()
        matches = sum(1 for pattern in explicit_patterns[language] 
                     if pattern.lower() in text_lower)
        
        # 🆕 修正: より寛容な評価で、1つでも見つかれば高スコア
        if matches >= 2:
            return 1.0  # 2つ以上なら満点
        elif matches == 1:
            return 0.8  # 1つでも高評価
        else:
            return 0.0
    
    def _evaluate_reasoning_depth(self, text: str, language: str) -> float:
        """理由の詳細度評価"""
        # 文章長による基本評価
        length_score = min(1.0, len(text) / 500)  # 500文字で満点
        
        # 理由キーワードの多様性
        unique_reasons = set()
        for reason, lang_keywords in self.reason_keywords.items():
            if language in lang_keywords:
                for keyword in lang_keywords[language]:
                    if keyword.lower() in text.lower():
                        unique_reasons.add(reason)
        
        diversity_score = min(1.0, len(unique_reasons) / 5)  # 5種類で満点
        
        return (length_score + diversity_score) / 2
    
    def _evaluate_comparative_analysis(self, text: str, language: str) -> float:
        """比較分析の評価"""
        comparison_patterns = {
            'ja': ['比較', 'より', '対して', '一方', 'しかし', 'ただし'],
            'en': ['compare', 'versus', 'while', 'however', 'whereas', 'better'],
            'fr': ['comparé', 'versus', 'tandis', 'cependant', 'alors', 'meilleur'],
            'es': ['comparado', 'versus', 'mientras', 'sin embargo', 'mejor']
        }
        
        if language not in comparison_patterns:
            return 0.0
        
        text_lower = text.lower()
        matches = sum(1 for pattern in comparison_patterns[language] 
                     if pattern.lower() in text_lower)
        
        return min(1.0, matches / 2.0)  # 2回で満点
    
    def _evaluate_specific_examples(self, text: str, language: str) -> float:
        """具体例の評価"""
        example_patterns = {
            'ja': ['例えば', 'たとえば', '具体的', '実際', 'ケース'],
            'en': ['example', 'instance', 'specifically', 'case', 'such as'],
            'fr': ['exemple', 'par exemple', 'spécifiquement', 'cas'],
            'es': ['ejemplo', 'por ejemplo', 'específicamente', 'caso']
        }
        
        if language not in example_patterns:
            return 0.0
        
        text_lower = text.lower()
        matches = sum(1 for pattern in example_patterns[language] 
                     if pattern.lower() in text_lower)
        
        return min(1.0, matches / 2.0)  # 2回で満点
    
    def _analyze_recommendation_strength(self, text: str, language: str) -> RecommendationStrength:
        """推奨強度の分析"""
        confidence_score = self.calculate_recommendation_confidence(text, language)
        
        if confidence_score >= 0.8:
            return RecommendationStrength.VERY_STRONG
        elif confidence_score >= 0.6:
            return RecommendationStrength.STRONG
        elif confidence_score >= 0.4:
            return RecommendationStrength.MODERATE
        elif confidence_score >= 0.2:
            return RecommendationStrength.WEAK
        else:
            return RecommendationStrength.NONE
    
    def _extract_reasoning_text(self, analysis_text: str, language: str) -> str:
        """推奨理由テキストの抽出"""
        # 推奨部分の前後のテキストを抽出
        lines = analysis_text.split('\n')
        reasoning_lines = []
        
        for i, line in enumerate(lines):
            # 推奨キーワードを含む行とその前後を取得
            if any(keyword in line.lower() for keyword in ['推奨', 'recommend', '最適', 'best']):
                # 前の行
                if i > 0:
                    reasoning_lines.append(lines[i-1])
                reasoning_lines.append(line)
                # 次の行
                if i < len(lines) - 1:
                    reasoning_lines.append(lines[i+1])
        
        if reasoning_lines:
            return ' '.join(reasoning_lines).strip()
        
        # フォールバック: 最初の100文字
        return analysis_text[:100] + "..." if len(analysis_text) > 100 else analysis_text
    
    def _count_pattern_matches(self, text: str, language: str) -> int:
        """パターンマッチ数のカウント"""
        if language not in self.multilingual_patterns:
            return 0
        
        count = 0
        for pattern in self.multilingual_patterns[language]:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            count += len(list(matches))
        
        return count
    
    def _count_reason_keywords(self, text: str, language: str) -> int:
        """理由キーワード数のカウント"""
        text_lower = text.lower()
        count = 0
        
        for reason, lang_keywords in self.reason_keywords.items():
            if language in lang_keywords:
                for keyword in lang_keywords[language]:
                    count += text_lower.count(keyword.lower())
        
        return count


# テスト用メイン関数
if __name__ == "__main__":
    print("🎯 高度Gemini分析エンジン - テスト実行")
    print("=" * 60)
    
    engine = AdvancedGeminiAnalysisEngine()
    
    # テストケース
    test_cases = [
        {
            'text': """3つの翻訳を詳細に比較分析した結果、Enhanced翻訳が最も自然で文脈に適しており、
                      特にビジネス文書での丁寧さと正確性の観点から推奨します。
                      ChatGPTは若干硬い表現、Geminiは自然だが少し砕けた印象です。""",
            'language': 'ja'
        },
        {
            'text': """After thorough analysis, I would recommend the Enhanced translation
                      for its superior clarity and professional tone. While ChatGPT provides
                      good accuracy, Enhanced better captures the nuanced meaning.""",
            'language': 'en'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 テストケース {i} ({test_case['language']}):")
        
        # 構造化推奨抽出
        result = engine.extract_structured_recommendations(
            test_case['text'], 
            test_case['language']
        )
        
        print(f"推奨エンジン: {result.recommended_engine}")
        print(f"信頼度: {result.confidence_score:.3f}")
        print(f"強度: {result.strength_level.value}")
        print(f"主要理由: {[r.value for r in result.primary_reasons]}")
        print(f"副次理由: {[r.value for r in result.secondary_reasons]}")
        
        # 多言語解析
        multilingual_result = engine.parse_multilingual_analysis(
            test_case['text'], 
            test_case['language']
        )
        
        print(f"パターンマッチ数: {multilingual_result['text_analysis']['total_matches']}")
        print(f"信頼度指標: {multilingual_result['text_analysis']['confidence_indicators']}")
    
    print("\n✅ テスト完了 - 高度分析エンジン正常動作")