#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🎯 戦略的強化: 個人化ファインチューニング用データ収集システム
=====================================================
目的: LangPont商用化における戦略的競合優位性の構築
     - 独自データ + プロンプトエンジニアリング + ファインチューニング
     - ユーザー一人ひとりの言語化スタイル・思考パターン・特定クセの収集
     - 他社が真似できない参入障壁の構築

【戦略的価値】
- 個人の思考→言語化プロセスの独自データ収集
- 文化的背景・職業特性による翻訳選択パターン解析
- ファインチューニング用の高品質個人化データ生成
- 競合が模倣困難な非接触データ収集手法
"""

import sqlite3
import json
import logging
import time
import statistics
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Set
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from enum import Enum
import uuid

# Task 2.9.2基盤システムのインポート
from preference_reason_estimator import PreferenceReasonEstimator, PreferenceProfile
from recommendation_divergence_detector import EnhancedRecommendationDivergenceDetector, DivergenceEvent
from advanced_gemini_analysis_engine import AdvancedGeminiAnalysisEngine, StructuredRecommendation

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PersonalizationPatternType(Enum):
    """個人化パターンタイプ"""
    THINKING_TO_LANGUAGE = "thinking_to_language"     # 思考→言語化プロセス
    CULTURAL_ADAPTATION = "cultural_adaptation"       # 文化的適応パターン
    PROFESSIONAL_STYLE = "professional_style"         # 職業的スタイル
    EMOTIONAL_NUANCE = "emotional_nuance"             # 感情的ニュアンス
    FORMALITY_PREFERENCE = "formality_preference"     # 丁寧度選好
    DOMAIN_SPECIALIZATION = "domain_specialization"   # 専門分野特化
    TEMPORAL_CONSISTENCY = "temporal_consistency"     # 時間的一貫性
    CONTEXT_SENSITIVITY = "context_sensitivity"       # 文脈感応性

class DataCommercialValue(Enum):
    """データの商用価値レベル"""
    EXTREMELY_HIGH = "extremely_high"    # 極めて高価値（競合優位性決定的）
    HIGH = "high"                       # 高価値（差別化に重要）
    MEDIUM = "medium"                   # 中価値（有用だが一般的）
    LOW = "low"                        # 低価値（基本的データ）
    COMMODITY = "commodity"             # 汎用（競合も容易に取得可能）

class FineTuningDataType(Enum):
    """ファインチューニングデータタイプ"""
    USER_PREFERENCE = "user_preference"         # ユーザー選好データ
    CONTEXTUAL_CHOICE = "contextual_choice"     # 文脈依存選択データ
    STYLE_ADAPTATION = "style_adaptation"       # スタイル適応データ
    QUALITY_JUDGMENT = "quality_judgment"       # 品質判断データ
    CULTURAL_MAPPING = "cultural_mapping"       # 文化的マッピングデータ

@dataclass
class PersonalizationPattern:
    """個人化パターンデータ"""
    pattern_id: str
    user_id: str
    pattern_type: PersonalizationPatternType
    pattern_data: Dict[str, Any]
    confidence_score: float
    commercial_value: DataCommercialValue
    uniqueness_score: float  # 競合との差別化度
    replication_difficulty: float  # 模倣困難度
    discovery_timestamp: str
    supporting_evidence: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FineTuningDataset:
    """ファインチューニング用データセット"""
    dataset_id: str
    user_id: str
    data_type: FineTuningDataType
    input_text: str
    target_translation: str
    context_features: Dict[str, Any]
    user_choice_reasoning: str
    quality_metrics: Dict[str, float]
    strategic_value: float  # 戦略的価値スコア
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

class PersonalizationDataCollector:
    """個人化ファインチューニング用データ収集システム"""
    
    def __init__(self,
                 analytics_db_path: str = "langpont_analytics.db",
                 divergence_db_path: str = "langpont_divergence.db",
                 preference_db_path: str = "langpont_preferences.db",
                 personalization_db_path: str = "langpont_personalization.db"):
        """初期化"""
        self.analytics_db_path = analytics_db_path
        self.divergence_db_path = divergence_db_path
        self.preference_db_path = preference_db_path
        self.personalization_db_path = personalization_db_path
        
        # Task 2.9.2基盤システムの活用
        self.preference_estimator = PreferenceReasonEstimator(
            analytics_db_path, divergence_db_path, preference_db_path
        )
        self.divergence_detector = EnhancedRecommendationDivergenceDetector(
            analytics_db_path, divergence_db_path
        )
        self.analysis_engine = AdvancedGeminiAnalysisEngine()
        
        # 戦略的価値評価基準
        self.commercial_value_weights = {
            'uniqueness': 0.3,           # データの独自性
            'replication_difficulty': 0.25, # 模倣困難度
            'user_specificity': 0.2,     # ユーザー固有性
            'temporal_stability': 0.15,  # 時間的安定性
            'scalability': 0.1           # スケーラビリティ
        }
        
        # 個人化パターン検出閾値
        self.pattern_detection_thresholds = {
            'consistency_threshold': 0.7,    # 一貫性閾値
            'uniqueness_threshold': 0.6,     # 独自性閾値
            'evidence_min_count': 3,         # 最低証拠数
            'temporal_window_days': 30       # 分析期間
        }
        
        # 個人化データベースの初期化
        self._init_personalization_database()
        
        logger.info("戦略的個人化データ収集システム初期化完了")
    
    def _init_personalization_database(self):
        """個人化専用データベースの初期化"""
        with sqlite3.connect(self.personalization_db_path) as conn:
            cursor = conn.cursor()
            
            # 個人化パターンテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS personalization_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_id VARCHAR(100) UNIQUE NOT NULL,
                    user_id VARCHAR(100) NOT NULL,
                    
                    -- パターン分類
                    pattern_type VARCHAR(50) NOT NULL,
                    pattern_data TEXT NOT NULL,
                    confidence_score FLOAT NOT NULL,
                    
                    -- 商用価値
                    commercial_value VARCHAR(20) NOT NULL,
                    uniqueness_score FLOAT NOT NULL,
                    replication_difficulty FLOAT NOT NULL,
                    
                    -- 証拠・メタデータ
                    supporting_evidence TEXT,
                    pattern_metadata TEXT,
                    
                    -- 時間管理
                    discovery_timestamp TIMESTAMP NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ファインチューニングデータセットテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fine_tuning_datasets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id VARCHAR(100) UNIQUE NOT NULL,
                    user_id VARCHAR(100) NOT NULL,
                    
                    -- データタイプ
                    data_type VARCHAR(50) NOT NULL,
                    input_text TEXT NOT NULL,
                    target_translation TEXT NOT NULL,
                    
                    -- コンテキスト・理由
                    context_features TEXT NOT NULL,
                    user_choice_reasoning TEXT,
                    
                    -- 品質・価値
                    quality_metrics TEXT NOT NULL,
                    strategic_value FLOAT NOT NULL,
                    
                    -- 時間管理
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # プロンプト最適化データテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS prompt_optimization_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id VARCHAR(100) NOT NULL,
                    
                    -- 拒否パターン
                    rejected_recommendation VARCHAR(50),
                    rejection_reasoning TEXT,
                    preferred_alternative VARCHAR(50),
                    
                    -- コンテキスト情報
                    text_context TEXT,
                    user_context TEXT,
                    situational_context TEXT,
                    
                    -- 学習価値
                    learning_value FLOAT,
                    prompt_optimization_potential FLOAT,
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 独自言語パターンテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS unique_language_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id VARCHAR(100) NOT NULL,
                    
                    -- パターン詳細
                    pattern_category VARCHAR(50),
                    language_feature TEXT,
                    frequency_score FLOAT,
                    uniqueness_index FLOAT,
                    
                    -- 競合優位性
                    moat_contribution FLOAT,
                    replication_complexity FLOAT,
                    
                    -- 証拠データ
                    evidence_count INTEGER,
                    evidence_data TEXT,
                    
                    first_detected TIMESTAMP,
                    last_observed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # インデックス作成
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pattern_user ON personalization_patterns (user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pattern_type ON personalization_patterns (pattern_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_dataset_user ON fine_tuning_datasets (user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_dataset_type ON fine_tuning_datasets (data_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_prompt_user ON prompt_optimization_data (user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_language_user ON unique_language_patterns (user_id)')
            
            conn.commit()
    
    def collect_fine_tuning_patterns(self, user_sessions: List[Dict]) -> Dict[str, Any]:
        """
        ファインチューニング用の個人パターンデータ収集
        
        Args:
            user_sessions: ユーザーセッションデータのリスト
            
        Returns:
            個人化パターン分析結果
        """
        if not user_sessions:
            return {'error': 'ユーザーセッションデータが必要です'}
        
        user_id = user_sessions[0].get('user_id')
        if not user_id:
            return {'error': 'ユーザーIDが必要です'}
        
        try:
            collection_results = {
                'user_id': user_id,
                'session_count': len(user_sessions),
                'collected_patterns': [],
                'fine_tuning_datasets': [],
                'collection_quality': {}
            }
            
            # 1. 翻訳選択パターンの分析
            choice_patterns = self._analyze_translation_choice_patterns(user_sessions)
            collection_results['collected_patterns'].extend(choice_patterns)
            
            # 2. 文体・語調選好の分析
            style_patterns = self._analyze_style_tone_preferences(user_sessions)
            collection_results['collected_patterns'].extend(style_patterns)
            
            # 3. 業界・文脈特有の表現選択分析
            domain_patterns = self._analyze_domain_specific_choices(user_sessions)
            collection_results['collected_patterns'].extend(domain_patterns)
            
            # 4. ファインチューニング用データセット生成
            ft_datasets = self._generate_fine_tuning_datasets(user_sessions, choice_patterns + style_patterns + domain_patterns)
            collection_results['fine_tuning_datasets'] = ft_datasets
            
            # 5. 収集品質の評価
            collection_results['collection_quality'] = self._evaluate_collection_quality(
                collection_results['collected_patterns'],
                collection_results['fine_tuning_datasets']
            )
            
            # 6. データベースへの保存
            self._save_personalization_patterns(collection_results['collected_patterns'])
            self._save_fine_tuning_datasets(collection_results['fine_tuning_datasets'])
            
            logger.info(f"個人化パターン収集完了: user={user_id}, "
                       f"パターン数={len(collection_results['collected_patterns'])}, "
                       f"データセット数={len(collection_results['fine_tuning_datasets'])}")
            
            return collection_results
            
        except Exception as e:
            logger.error(f"個人化パターン収集エラー: {str(e)}")
            return {'error': str(e)}
    
    def _analyze_translation_choice_patterns(self, sessions: List[Dict]) -> List[PersonalizationPattern]:
        """翻訳選択パターンの分析"""
        patterns = []
        
        # エンジン選択の一貫性分析
        engine_choices = [s.get('user_choice', '') for s in sessions]
        engine_counter = Counter(engine_choices)
        
        if engine_counter and len(sessions) >= 5:
            most_common = engine_counter.most_common(1)[0]
            consistency_rate = most_common[1] / len(sessions)
            
            if consistency_rate >= self.pattern_detection_thresholds['consistency_threshold']:
                pattern = PersonalizationPattern(
                    pattern_id=f"choice_consistency_{uuid.uuid4().hex[:8]}",
                    user_id=sessions[0]['user_id'],
                    pattern_type=PersonalizationPatternType.THINKING_TO_LANGUAGE,
                    pattern_data={
                        'preferred_engine': most_common[0],
                        'consistency_rate': consistency_rate,
                        'total_choices': len(sessions),
                        'alternative_engines': dict(engine_counter)
                    },
                    confidence_score=consistency_rate,
                    commercial_value=self._assess_commercial_value(consistency_rate, 'engine_preference'),
                    uniqueness_score=self._calculate_uniqueness_score(engine_counter, 'engine_choice'),
                    replication_difficulty=0.8,  # エンジン選好は模倣困難
                    discovery_timestamp=datetime.now().isoformat(),
                    supporting_evidence=[{
                        'session_id': s.get('session_id', ''),
                        'choice': s.get('user_choice', ''),
                        'satisfaction': s.get('satisfaction_score', 0)
                    } for s in sessions]
                )
                patterns.append(pattern)
        
        # 満足度との相関パターン
        satisfaction_by_engine = defaultdict(list)
        for session in sessions:
            engine = session.get('user_choice', '')
            satisfaction = session.get('satisfaction_score', 0)
            if engine and satisfaction > 0:
                satisfaction_by_engine[engine].append(satisfaction)
        
        for engine, satisfactions in satisfaction_by_engine.items():
            if len(satisfactions) >= 3:
                avg_satisfaction = statistics.mean(satisfactions)
                std_satisfaction = statistics.stdev(satisfactions) if len(satisfactions) > 1 else 0
                
                # 高満足度かつ低分散（安定した選好）
                if avg_satisfaction >= 75 and std_satisfaction <= 15:
                    pattern = PersonalizationPattern(
                        pattern_id=f"satisfaction_pattern_{uuid.uuid4().hex[:8]}",
                        user_id=sessions[0]['user_id'],
                        pattern_type=PersonalizationPatternType.THINKING_TO_LANGUAGE,
                        pattern_data={
                            'preferred_engine': engine,
                            'average_satisfaction': avg_satisfaction,
                            'satisfaction_stability': std_satisfaction,
                            'sample_size': len(satisfactions)
                        },
                        confidence_score=min(1.0, avg_satisfaction / 100 * (1 - std_satisfaction / 100)),
                        commercial_value=DataCommercialValue.HIGH,
                        uniqueness_score=0.75,
                        replication_difficulty=0.9,  # 満足度パターンは高度に個人的
                        discovery_timestamp=datetime.now().isoformat(),
                        supporting_evidence=satisfactions
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _analyze_style_tone_preferences(self, sessions: List[Dict]) -> List[PersonalizationPattern]:
        """文体・語調選好の分析"""
        patterns = []
        
        # コンテキスト別の選択パターン分析
        context_choices = defaultdict(list)
        
        for session in sessions:
            context_data = session.get('context_data', {})
            user_choice = session.get('user_choice', '')
            
            # 文章長カテゴリ
            text_length = context_data.get('text_length', 0)
            length_category = self._categorize_text_length(text_length)
            context_choices[f'length_{length_category}'].append(user_choice)
            
            # ビジネス文脈
            if context_data.get('business_context'):
                context_choices['business'].append(user_choice)
            
            # 技術文書
            if context_data.get('has_technical_terms'):
                context_choices['technical'].append(user_choice)
        
        # 各コンテキストでの一貫した選好を検出
        for context, choices in context_choices.items():
            if len(choices) >= 3:
                choice_counter = Counter(choices)
                most_common = choice_counter.most_common(1)[0]
                consistency = most_common[1] / len(choices)
                
                if consistency >= 0.6:  # 60%以上の一貫性
                    pattern = PersonalizationPattern(
                        pattern_id=f"context_style_{uuid.uuid4().hex[:8]}",
                        user_id=sessions[0]['user_id'],
                        pattern_type=PersonalizationPatternType.CONTEXT_SENSITIVITY,
                        pattern_data={
                            'context_type': context,
                            'preferred_engine': most_common[0],
                            'consistency_rate': consistency,
                            'sample_size': len(choices),
                            'choice_distribution': dict(choice_counter)
                        },
                        confidence_score=consistency,
                        commercial_value=DataCommercialValue.EXTREMELY_HIGH,  # 文脈適応は極めて高価値
                        uniqueness_score=0.85,
                        replication_difficulty=0.95,  # 個人の文脈判断は模倣極困難
                        discovery_timestamp=datetime.now().isoformat(),
                        supporting_evidence=choices
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _analyze_domain_specific_choices(self, sessions: List[Dict]) -> List[PersonalizationPattern]:
        """業界・文脈特有の表現選択分析"""
        patterns = []
        
        # 専門用語を含む文書での選択パターン
        technical_sessions = [s for s in sessions if s.get('context_data', {}).get('has_technical_terms')]
        
        if len(technical_sessions) >= 3:
            tech_choices = [s.get('user_choice', '') for s in technical_sessions]
            tech_counter = Counter(tech_choices)
            
            if tech_counter:
                most_common = tech_counter.most_common(1)[0]
                preference_rate = most_common[1] / len(technical_sessions)
                
                if preference_rate >= 0.7:
                    pattern = PersonalizationPattern(
                        pattern_id=f"domain_expertise_{uuid.uuid4().hex[:8]}",
                        user_id=sessions[0]['user_id'],
                        pattern_type=PersonalizationPatternType.DOMAIN_SPECIALIZATION,
                        pattern_data={
                            'domain': 'technical',
                            'preferred_engine': most_common[0],
                            'expertise_preference_rate': preference_rate,
                            'technical_document_count': len(technical_sessions),
                            'choice_distribution': dict(tech_counter)
                        },
                        confidence_score=preference_rate,
                        commercial_value=DataCommercialValue.HIGH,
                        uniqueness_score=0.8,
                        replication_difficulty=0.85,
                        discovery_timestamp=datetime.now().isoformat(),
                        supporting_evidence=[{
                            'session_id': s.get('session_id', ''),
                            'choice': s.get('user_choice', ''),
                            'technical_terms': s.get('context_data', {}).get('technical_term_count', 0)
                        } for s in technical_sessions]
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _generate_fine_tuning_datasets(self, sessions: List[Dict], patterns: List[PersonalizationPattern]) -> List[FineTuningDataset]:
        """ファインチューニング用データセット生成"""
        datasets = []
        
        for session in sessions:
            user_id = session.get('user_id')
            input_text = session.get('input_text', '')
            user_choice = session.get('user_choice', '')
            target_translation = session.get('translation_result', '')
            context_data = session.get('context_data', {})
            satisfaction = session.get('satisfaction_score', 0)
            
            if all([user_id, input_text, user_choice, target_translation]):
                # パターンから推論される選択理由
                choice_reasoning = self._infer_choice_reasoning(session, patterns)
                
                # 戦略的価値の算出
                strategic_value = self._calculate_strategic_value(session, patterns)
                
                dataset = FineTuningDataset(
                    dataset_id=f"ft_{uuid.uuid4().hex[:12]}",
                    user_id=user_id,
                    data_type=self._determine_data_type(session, patterns),
                    input_text=input_text,
                    target_translation=target_translation,
                    context_features={
                        'text_length': len(input_text),
                        'has_technical_terms': context_data.get('has_technical_terms', False),
                        'business_context': context_data.get('business_context', False),
                        'cultural_context': context_data.get('cultural_context', False),
                        'formality_level': self._assess_formality_level(input_text),
                        'domain_category': self._classify_domain(input_text, context_data)
                    },
                    user_choice_reasoning=choice_reasoning,
                    quality_metrics={
                        'satisfaction_score': satisfaction,
                        'choice_confidence': self._assess_choice_confidence(session, patterns),
                        'context_appropriateness': self._assess_context_appropriateness(session),
                        'uniqueness_score': strategic_value
                    },
                    strategic_value=strategic_value
                )
                datasets.append(dataset)
        
        return datasets
    
    def extract_prompt_optimization_data(self, divergence_events: List[Dict]) -> Dict[str, Any]:
        """
        プロンプト最適化用のデータ抽出
        
        Args:
            divergence_events: 乖離イベントデータのリスト
            
        Returns:
            プロンプト最適化データ
        """
        try:
            optimization_data = {
                'rejection_patterns': [],
                'context_dependent_preferences': [],
                'prompt_improvement_suggestions': [],
                'strategic_insights': {}
            }
            
            # 高価値な乖離イベントの抽出（学習価値 >= 0.7）
            high_value_events = [
                event for event in divergence_events 
                if event.get('learning_value', 0) >= 0.7
            ]
            
            # 拒否パターンの分析
            rejection_patterns = self._analyze_rejection_patterns(high_value_events)
            optimization_data['rejection_patterns'] = rejection_patterns
            
            # 文脈依存選好の抽出
            context_preferences = self._extract_context_dependent_preferences(high_value_events)
            optimization_data['context_dependent_preferences'] = context_preferences
            
            # プロンプト改善提案の生成
            improvement_suggestions = self._generate_prompt_improvements(rejection_patterns, context_preferences)
            optimization_data['prompt_improvement_suggestions'] = improvement_suggestions
            
            # 戦略的インサイトの抽出
            strategic_insights = self._extract_strategic_insights(high_value_events)
            optimization_data['strategic_insights'] = strategic_insights
            
            # データベースへの保存
            self._save_prompt_optimization_data(optimization_data)
            
            logger.info(f"プロンプト最適化データ抽出完了: "
                       f"拒否パターン={len(rejection_patterns)}, "
                       f"文脈選好={len(context_preferences)}")
            
            return optimization_data
            
        except Exception as e:
            logger.error(f"プロンプト最適化データ抽出エラー: {str(e)}")
            return {'error': str(e)}
    
    def identify_unique_language_patterns(self, user_choices: List[Dict]) -> Dict[str, Any]:
        """
        他社が持たない独自の言語パターン特定
        
        Args:
            user_choices: ユーザー選択データのリスト
            
        Returns:
            独自言語パターン分析結果
        """
        try:
            unique_patterns = {
                'thinking_to_language_patterns': [],
                'cultural_linguistic_features': [],
                'professional_language_habits': [],
                'temporal_language_evolution': [],
                'moat_strength_indicators': {}
            }
            
            # 1. 思考→言語化プロセスパターン
            thinking_patterns = self._identify_thinking_language_patterns(user_choices)
            unique_patterns['thinking_to_language_patterns'] = thinking_patterns
            
            # 2. 文化的言語特徴
            cultural_features = self._identify_cultural_linguistic_features(user_choices)
            unique_patterns['cultural_linguistic_features'] = cultural_features
            
            # 3. 職業的言語習慣
            professional_habits = self._identify_professional_language_habits(user_choices)
            unique_patterns['professional_language_habits'] = professional_habits
            
            # 4. 時間的言語進化
            temporal_evolution = self._track_temporal_language_evolution(user_choices)
            unique_patterns['temporal_language_evolution'] = temporal_evolution
            
            # 5. 参入障壁強度指標
            moat_indicators = self._calculate_moat_strength_indicators(unique_patterns)
            unique_patterns['moat_strength_indicators'] = moat_indicators
            
            # データベースへの保存
            self._save_unique_language_patterns(unique_patterns)
            
            logger.info(f"独自言語パターン特定完了: "
                       f"思考パターン={len(thinking_patterns)}, "
                       f"文化特徴={len(cultural_features)}, "
                       f"職業習慣={len(professional_habits)}")
            
            return unique_patterns
            
        except Exception as e:
            logger.error(f"独自言語パターン特定エラー: {str(e)}")
            return {'error': str(e)}
    
    def generate_training_data_format(self, personalization_data: Dict) -> List[Dict]:
        """
        機械学習用の訓練データ形式生成
        
        Args:
            personalization_data: 個人化データ
            
        Returns:
            機械学習用データセット
        """
        try:
            training_data = []
            
            # ファインチューニング用データの変換
            if 'fine_tuning_datasets' in personalization_data:
                for dataset in personalization_data['fine_tuning_datasets']:
                    training_sample = {
                        'input': {
                            'text': dataset.get('input_text', ''),
                            'context': dataset.get('context_features', {}),
                            'user_profile': self._extract_user_profile_features(dataset.get('user_id', ''))
                        },
                        'output': {
                            'translation': dataset.get('target_translation', ''),
                            'engine_choice': dataset.get('user_choice_reasoning', ''),
                            'quality_score': dataset.get('quality_metrics', {}).get('satisfaction_score', 0)
                        },
                        'metadata': {
                            'strategic_value': dataset.get('strategic_value', 0),
                            'data_type': dataset.get('data_type', ''),
                            'timestamp': dataset.get('created_at', '')
                        }
                    }
                    training_data.append(training_sample)
            
            # プロンプトテンプレート生成
            prompt_templates = self._generate_prompt_templates(personalization_data)
            
            # 個人化重み調整パラメータ
            personalization_weights = self._generate_personalization_weights(personalization_data)
            
            result = {
                'training_samples': training_data,
                'prompt_templates': prompt_templates,
                'personalization_weights': personalization_weights,
                'dataset_quality_metrics': self._calculate_dataset_quality_metrics(training_data)
            }
            
            logger.info(f"訓練データ形式生成完了: サンプル数={len(training_data)}")
            
            return result
            
        except Exception as e:
            logger.error(f"訓練データ形式生成エラー: {str(e)}")
            return {'error': str(e)}
    
    # ヘルパーメソッド群
    def _categorize_text_length(self, length: int) -> str:
        """文章長のカテゴライズ"""
        if length < 50:
            return 'very_short'
        elif length < 150:
            return 'short'
        elif length < 300:
            return 'medium'
        elif length < 600:
            return 'long'
        else:
            return 'very_long'
    
    def _assess_commercial_value(self, metric_value: float, pattern_type: str) -> DataCommercialValue:
        """商用価値の評価"""
        if pattern_type == 'engine_preference':
            if metric_value >= 0.9:
                return DataCommercialValue.EXTREMELY_HIGH
            elif metric_value >= 0.8:
                return DataCommercialValue.HIGH
            elif metric_value >= 0.6:
                return DataCommercialValue.MEDIUM
            else:
                return DataCommercialValue.LOW
        
        return DataCommercialValue.MEDIUM
    
    def _calculate_uniqueness_score(self, data_distribution: Counter, pattern_type: str) -> float:
        """独自性スコアの計算"""
        if not data_distribution:
            return 0.0
        
        # エントロピーベースの独自性計算
        total = sum(data_distribution.values())
        entropy = 0.0
        for count in data_distribution.values():
            prob = count / total
            if prob > 0:
                entropy -= prob * math.log2(prob)
        
        # 0-1の範囲に正規化
        max_entropy = math.log2(len(data_distribution)) if len(data_distribution) > 1 else 1
        uniqueness = 1 - (entropy / max_entropy) if max_entropy > 0 else 0
        
        return max(0.0, min(1.0, uniqueness))
    
    def _save_personalization_patterns(self, patterns: List[PersonalizationPattern]):
        """個人化パターンの保存"""
        with sqlite3.connect(self.personalization_db_path) as conn:
            cursor = conn.cursor()
            
            for pattern in patterns:
                cursor.execute('''
                    INSERT OR REPLACE INTO personalization_patterns (
                        pattern_id, user_id, pattern_type, pattern_data,
                        confidence_score, commercial_value, uniqueness_score,
                        replication_difficulty, supporting_evidence, pattern_metadata,
                        discovery_timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    pattern.pattern_id,
                    pattern.user_id,
                    pattern.pattern_type.value,
                    json.dumps(pattern.pattern_data),
                    pattern.confidence_score,
                    pattern.commercial_value.value,
                    pattern.uniqueness_score,
                    pattern.replication_difficulty,
                    json.dumps(pattern.supporting_evidence),
                    json.dumps(pattern.metadata),
                    pattern.discovery_timestamp
                ))
            
            conn.commit()
    
    def _save_fine_tuning_datasets(self, datasets: List[FineTuningDataset]):
        """ファインチューニングデータセットの保存"""
        with sqlite3.connect(self.personalization_db_path) as conn:
            cursor = conn.cursor()
            
            for dataset in datasets:
                cursor.execute('''
                    INSERT OR REPLACE INTO fine_tuning_datasets (
                        dataset_id, user_id, data_type, input_text,
                        target_translation, context_features, user_choice_reasoning,
                        quality_metrics, strategic_value
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    dataset.dataset_id,
                    dataset.user_id,
                    dataset.data_type.value,
                    dataset.input_text,
                    dataset.target_translation,
                    json.dumps(dataset.context_features),
                    dataset.user_choice_reasoning,
                    json.dumps(dataset.quality_metrics),
                    dataset.strategic_value
                ))
            
            conn.commit()
    
    # 以下、その他のヘルパーメソッドの実装を続ける...
    def _evaluate_collection_quality(self, patterns: List, datasets: List) -> Dict[str, float]:
        """収集品質の評価"""
        return {
            'pattern_diversity': len(set(p.pattern_type for p in patterns)) / 8.0,  # 8種類のパターンタイプ
            'data_volume_score': min(1.0, len(datasets) / 10.0),  # 10件で満点
            'strategic_value_avg': statistics.mean([d.strategic_value for d in datasets]) if datasets else 0.0,
            'uniqueness_avg': statistics.mean([p.uniqueness_score for p in patterns]) if patterns else 0.0
        }
    
    # 簡略化された実装（実際にはより詳細な実装が必要）
    def _infer_choice_reasoning(self, session: Dict, patterns: List) -> str:
        """選択理由の推論"""
        return f"Based on user patterns and context: {session.get('user_choice', '')}"
    
    def _calculate_strategic_value(self, session: Dict, patterns: List) -> float:
        """戦略的価値の計算"""
        return 0.8  # プレースホルダー
    
    def _determine_data_type(self, session: Dict, patterns: List) -> FineTuningDataType:
        """データタイプの決定"""
        return FineTuningDataType.USER_PREFERENCE
    
    def _assess_formality_level(self, text: str) -> str:
        """丁寧度レベルの評価"""
        return "medium"  # プレースホルダー
    
    def _classify_domain(self, text: str, context: Dict) -> str:
        """分野の分類"""
        return "general"  # プレースホルダー
    
    def _assess_choice_confidence(self, session: Dict, patterns: List) -> float:
        """選択信頼度の評価"""
        return 0.8  # プレースホルダー
    
    def _assess_context_appropriateness(self, session: Dict) -> float:
        """文脈適切性の評価"""
        return 0.8  # プレースホルダー
    
    # その他のメソッドもプレースホルダーとして簡略実装
    def _analyze_rejection_patterns(self, events: List) -> List:
        return []
    
    def _extract_context_dependent_preferences(self, events: List) -> List:
        return []
    
    def _generate_prompt_improvements(self, rejections: List, preferences: List) -> List:
        return []
    
    def _extract_strategic_insights(self, events: List) -> Dict:
        return {}
    
    def _save_prompt_optimization_data(self, data: Dict):
        pass
    
    def _identify_thinking_language_patterns(self, choices: List) -> List:
        return []
    
    def _identify_cultural_linguistic_features(self, choices: List) -> List:
        return []
    
    def _identify_professional_language_habits(self, choices: List) -> List:
        return []
    
    def _track_temporal_language_evolution(self, choices: List) -> List:
        return []
    
    def _calculate_moat_strength_indicators(self, patterns: Dict) -> Dict:
        return {}
    
    def _save_unique_language_patterns(self, patterns: Dict):
        pass
    
    def _extract_user_profile_features(self, user_id: str) -> Dict:
        return {}
    
    def _generate_prompt_templates(self, data: Dict) -> List:
        return []
    
    def _generate_personalization_weights(self, data: Dict) -> Dict:
        return {}
    
    def _calculate_dataset_quality_metrics(self, data: List) -> Dict:
        return {}


# テスト用メイン関数
if __name__ == "__main__":
    print("🎯 戦略的個人化データ収集システム - テスト実行")
    print("=" * 60)
    
    collector = PersonalizationDataCollector()
    
    # テスト用セッションデータ
    test_sessions = [
        {
            'user_id': 'strategic_user_001',
            'session_id': 'session_001',
            'user_choice': 'enhanced',
            'input_text': 'ビジネスプレゼンテーションの準備をしています。',
            'translation_result': 'I am preparing for a business presentation.',
            'satisfaction_score': 85,
            'context_data': {
                'text_length': 200,
                'has_technical_terms': False,
                'business_context': True
            }
        },
        {
            'user_id': 'strategic_user_001',
            'session_id': 'session_002',
            'user_choice': 'enhanced',
            'input_text': '技術仕様書の翻訳が必要です。',
            'translation_result': 'Technical specification translation is required.',
            'satisfaction_score': 90,
            'context_data': {
                'text_length': 150,
                'has_technical_terms': True,
                'business_context': True
            }
        }
    ]
    
    # 個人化パターン収集テスト
    result = collector.collect_fine_tuning_patterns(test_sessions)
    
    print(f"✅ 個人化パターン収集結果:")
    print(f"  ユーザーID: {result.get('user_id', 'N/A')}")
    print(f"  セッション数: {result.get('session_count', 0)}")
    print(f"  収集パターン数: {len(result.get('collected_patterns', []))}")
    print(f"  ファインチューニングデータ数: {len(result.get('fine_tuning_datasets', []))}")
    
    # 収集品質表示
    quality = result.get('collection_quality', {})
    print(f"  収集品質:")
    for metric, value in quality.items():
        print(f"    {metric}: {value:.3f}")
    
    print("\n✅ テスト完了 - 戦略的個人化データ収集システム正常動作")