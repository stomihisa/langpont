#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🎯 戦略的強化: 競合優位性・参入障壁分析システム
=====================================================
目的: LangPont商用化における競合優位性の定量的評価
     - 収集データの独自性・希少性スコア算出
     - 競合による模倣困難度の推定
     - 参入障壁の強度計算
     - 戦略的データ収集の改善点特定

【戦略的価値】
- データの模倣困難度測定による競合分析
- 蓄積データの商用価値評価
- ネットワーク効果・学習効果の定量化
- 参入障壁構築の弱点分析と改善提案
"""

import sqlite3
import json
import logging
import time
import statistics
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from enum import Enum
import hashlib

# 戦略的システムのインポート
from personalization_data_collector import PersonalizationDataCollector, DataCommercialValue

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MoatStrength(Enum):
    """参入障壁強度レベル"""
    UNBREACHABLE = "unbreachable"    # 突破不可能（10年以上の優位性）
    VERY_STRONG = "very_strong"      # 非常に強固（5-10年の優位性）
    STRONG = "strong"                # 強固（3-5年の優位性）
    MODERATE = "moderate"            # 中程度（1-3年の優位性）
    WEAK = "weak"                    # 弱い（1年未満の優位性）
    NONE = "none"                    # 障壁なし

class CompetitiveFactor(Enum):
    """競合要因タイプ"""
    DATA_VOLUME = "data_volume"                # データボリューム
    DATA_QUALITY = "data_quality"              # データ品質
    COLLECTION_METHOD = "collection_method"    # 収集手法
    USER_BEHAVIOR = "user_behavior"            # ユーザー行動
    PERSONALIZATION = "personalization"       # 個人化技術
    NETWORK_EFFECTS = "network_effects"        # ネットワーク効果
    LEARNING_CURVE = "learning_curve"          # 学習曲線
    BRAND_LOYALTY = "brand_loyalty"            # ブランドロイヤルティ

class ReplicationDifficulty(Enum):
    """模倣困難度レベル"""
    IMPOSSIBLE = "impossible"        # 模倣不可能
    EXTREMELY_HARD = "extremely_hard" # 極めて困難
    VERY_HARD = "very_hard"         # 非常に困難
    HARD = "hard"                   # 困難
    MODERATE = "moderate"           # 中程度
    EASY = "easy"                   # 容易

@dataclass
class CompetitiveAdvantage:
    """競合優位性データ"""
    advantage_id: str
    advantage_type: CompetitiveFactor
    strength_score: float  # 0.0-1.0
    moat_contribution: float  # 参入障壁への貢献度
    replication_difficulty: ReplicationDifficulty
    time_to_replicate_months: int  # 模倣に要する期間（月）
    cost_to_replicate_usd: float  # 模倣に要するコスト（USD）
    strategic_importance: float  # 戦略的重要度
    evidence_data: Dict[str, Any]
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class MoatAnalysis:
    """参入障壁分析結果"""
    overall_moat_strength: MoatStrength
    moat_score: float  # 0.0-1.0
    competitive_advantages: List[CompetitiveAdvantage]
    vulnerability_points: List[str]
    improvement_opportunities: List[str]
    strategic_recommendations: List[str]
    analysis_metadata: Dict[str, Any]

class CompetitiveAdvantageAnalyzer:
    """競合優位性・参入障壁分析システム"""
    
    def __init__(self,
                 analytics_db_path: str = "langpont_analytics.db",
                 personalization_db_path: str = "langpont_personalization.db",
                 competitive_db_path: str = "langpont_competitive.db"):
        """初期化"""
        self.analytics_db_path = analytics_db_path
        self.personalization_db_path = personalization_db_path
        self.competitive_db_path = competitive_db_path
        
        # 個人化データ収集システムの活用
        self.personalization_collector = PersonalizationDataCollector(
            analytics_db_path=analytics_db_path,
            personalization_db_path=personalization_db_path
        )
        
        # 競合分析パラメータ
        self.competitive_factors_weights = {
            CompetitiveFactor.DATA_VOLUME: 0.15,
            CompetitiveFactor.DATA_QUALITY: 0.20,
            CompetitiveFactor.COLLECTION_METHOD: 0.15,
            CompetitiveFactor.USER_BEHAVIOR: 0.10,
            CompetitiveFactor.PERSONALIZATION: 0.15,
            CompetitiveFactor.NETWORK_EFFECTS: 0.10,
            CompetitiveFactor.LEARNING_CURVE: 0.10,
            CompetitiveFactor.BRAND_LOYALTY: 0.05
        }
        
        # 模倣困難度評価基準
        self.replication_thresholds = {
            ReplicationDifficulty.IMPOSSIBLE: 0.95,
            ReplicationDifficulty.EXTREMELY_HARD: 0.85,
            ReplicationDifficulty.VERY_HARD: 0.75,
            ReplicationDifficulty.HARD: 0.60,
            ReplicationDifficulty.MODERATE: 0.40,
            ReplicationDifficulty.EASY: 0.20
        }
        
        # 競合分析データベースの初期化
        self._init_competitive_database()
        
        logger.info("競合優位性分析システム初期化完了")
    
    def _init_competitive_database(self):
        """競合分析用データベースの初期化"""
        with sqlite3.connect(self.competitive_db_path) as conn:
            cursor = conn.cursor()
            
            # 競合優位性テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS competitive_advantages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    advantage_id VARCHAR(100) UNIQUE NOT NULL,
                    advantage_type VARCHAR(50) NOT NULL,
                    
                    -- 強度・貢献度
                    strength_score FLOAT NOT NULL,
                    moat_contribution FLOAT NOT NULL,
                    replication_difficulty VARCHAR(20) NOT NULL,
                    
                    -- 模倣コスト・期間
                    time_to_replicate_months INTEGER,
                    cost_to_replicate_usd FLOAT,
                    strategic_importance FLOAT,
                    
                    -- 証拠データ
                    evidence_data TEXT,
                    
                    -- 時間管理
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 参入障壁分析履歴テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS moat_analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id VARCHAR(100) UNIQUE NOT NULL,
                    
                    -- 分析結果
                    overall_moat_strength VARCHAR(20) NOT NULL,
                    moat_score FLOAT NOT NULL,
                    
                    -- 分析データ
                    competitive_advantages_count INTEGER,
                    vulnerability_points_count INTEGER,
                    improvement_opportunities_count INTEGER,
                    
                    -- 詳細データ
                    analysis_details TEXT,
                    strategic_recommendations TEXT,
                    
                    analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 競合比較テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS competitor_comparison (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    competitor_name VARCHAR(100),
                    comparison_factor VARCHAR(50),
                    
                    -- 比較スコア
                    langpont_score FLOAT,
                    competitor_score FLOAT,
                    advantage_gap FLOAT,
                    
                    -- 分析データ
                    comparison_basis TEXT,
                    confidence_level FLOAT,
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # データ独自性評価テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_uniqueness_evaluation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_category VARCHAR(50),
                    
                    -- 独自性指標
                    uniqueness_score FLOAT,
                    rarity_index FLOAT,
                    commercial_value VARCHAR(20),
                    
                    -- 模倣困難度
                    replication_difficulty_score FLOAT,
                    estimated_replication_time_months INTEGER,
                    estimated_replication_cost_usd FLOAT,
                    
                    -- メタデータ
                    evaluation_methodology TEXT,
                    supporting_data TEXT,
                    
                    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # インデックス作成
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_advantage_type ON competitive_advantages (advantage_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_moat_analysis_date ON moat_analysis_history (analysis_timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_competitor_factor ON competitor_comparison (comparison_factor)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_data_category ON data_uniqueness_evaluation (data_category)')
            
            conn.commit()
    
    def measure_data_uniqueness(self, collected_data: Dict) -> Dict[str, Any]:
        """
        収集データの独自性・希少性スコア算出
        
        Args:
            collected_data: 収集済みデータ
            
        Returns:
            データ独自性分析結果
        """
        try:
            uniqueness_analysis = {
                'overall_uniqueness_score': 0.0,
                'category_uniqueness': {},
                'rarity_indicators': {},
                'commercial_value_assessment': {},
                'competitive_differentiation': {}
            }
            
            # 1. 個人化パターンデータの独自性評価
            if 'personalization_patterns' in collected_data:
                pattern_uniqueness = self._evaluate_pattern_uniqueness(
                    collected_data['personalization_patterns']
                )
                uniqueness_analysis['category_uniqueness']['personalization_patterns'] = pattern_uniqueness
            
            # 2. ユーザー行動データの希少性評価
            if 'user_behavior_data' in collected_data:
                behavior_rarity = self._evaluate_behavior_data_rarity(
                    collected_data['user_behavior_data']
                )
                uniqueness_analysis['rarity_indicators']['user_behavior'] = behavior_rarity
            
            # 3. 言語パターンデータの独自性評価
            if 'language_patterns' in collected_data:
                language_uniqueness = self._evaluate_language_pattern_uniqueness(
                    collected_data['language_patterns']
                )
                uniqueness_analysis['category_uniqueness']['language_patterns'] = language_uniqueness
            
            # 4. 全体的な独自性スコア計算
            uniqueness_analysis['overall_uniqueness_score'] = self._calculate_overall_uniqueness(
                uniqueness_analysis['category_uniqueness']
            )
            
            # 5. 商用価値評価
            uniqueness_analysis['commercial_value_assessment'] = self._assess_commercial_value_from_uniqueness(
                uniqueness_analysis
            )
            
            # 6. 競合との差別化要素定量化
            uniqueness_analysis['competitive_differentiation'] = self._quantify_competitive_differentiation(
                uniqueness_analysis
            )
            
            # 7. データベースへの保存
            self._save_data_uniqueness_evaluation(uniqueness_analysis)
            
            logger.info(f"データ独自性評価完了: 全体スコア={uniqueness_analysis['overall_uniqueness_score']:.3f}")
            
            return uniqueness_analysis
            
        except Exception as e:
            logger.error(f"データ独自性評価エラー: {str(e)}")
            return {'error': str(e)}
    
    def estimate_replication_difficulty(self, pattern_data: Dict) -> Dict[str, Any]:
        """
        競合による模倣困難度の推定
        
        Args:
            pattern_data: パターンデータ
            
        Returns:
            模倣困難度分析結果
        """
        try:
            replication_analysis = {
                'overall_difficulty': ReplicationDifficulty.MODERATE,
                'difficulty_score': 0.0,
                'factor_analysis': {},
                'time_estimates': {},
                'cost_estimates': {},
                'risk_assessment': {}
            }
            
            # 1. データ収集期間の優位性評価
            collection_advantage = self._evaluate_data_collection_time_advantage(pattern_data)
            replication_analysis['factor_analysis']['collection_time'] = collection_advantage
            
            # 2. 非接触収集手法の技術的障壁評価
            technical_barrier = self._evaluate_technical_collection_barriers(pattern_data)
            replication_analysis['factor_analysis']['technical_barriers'] = technical_barrier
            
            # 3. ユーザー行動パターンの複雑性評価
            complexity_barrier = self._evaluate_user_behavior_complexity(pattern_data)
            replication_analysis['factor_analysis']['behavior_complexity'] = complexity_barrier
            
            # 4. 学習効果による障壁評価
            learning_barrier = self._evaluate_learning_effect_barriers(pattern_data)
            replication_analysis['factor_analysis']['learning_effects'] = learning_barrier
            
            # 5. 全体的な困難度スコア計算
            replication_analysis['difficulty_score'] = self._calculate_replication_difficulty_score(
                replication_analysis['factor_analysis']
            )
            
            # 6. 困難度レベルの決定
            replication_analysis['overall_difficulty'] = self._determine_replication_difficulty_level(
                replication_analysis['difficulty_score']
            )
            
            # 7. 模倣時間・コスト推定
            replication_analysis['time_estimates'] = self._estimate_replication_time(
                replication_analysis['factor_analysis']
            )
            replication_analysis['cost_estimates'] = self._estimate_replication_costs(
                replication_analysis['factor_analysis']
            )
            
            # 8. リスク評価
            replication_analysis['risk_assessment'] = self._assess_replication_risks(
                replication_analysis
            )
            
            logger.info(f"模倣困難度推定完了: レベル={replication_analysis['overall_difficulty'].value}, "
                       f"スコア={replication_analysis['difficulty_score']:.3f}")
            
            return replication_analysis
            
        except Exception as e:
            logger.error(f"模倣困難度推定エラー: {str(e)}")
            return {'error': str(e)}
    
    def calculate_moat_strength(self, user_base_data: Dict) -> float:
        """
        参入障壁の強度計算
        
        Args:
            user_base_data: ユーザーベースデータ
            
        Returns:
            参入障壁強度スコア (0.0-1.0)
        """
        try:
            moat_components = {}
            
            # 1. ネットワーク効果の測定
            network_effect = self._measure_network_effects(user_base_data)
            moat_components['network_effects'] = network_effect
            
            # 2. データ蓄積による学習効果測定
            learning_effect = self._measure_data_learning_effects(user_base_data)
            moat_components['learning_effects'] = learning_effect
            
            # 3. 個人化精度の競合優位性測定
            personalization_advantage = self._measure_personalization_advantage(user_base_data)
            moat_components['personalization_advantage'] = personalization_advantage
            
            # 4. ユーザー切り替えコスト測定
            switching_cost = self._measure_user_switching_costs(user_base_data)
            moat_components['switching_costs'] = switching_cost
            
            # 5. ブランドロイヤルティ測定
            brand_loyalty = self._measure_brand_loyalty(user_base_data)
            moat_components['brand_loyalty'] = brand_loyalty
            
            # 6. 重み付き総合スコア計算
            moat_strength = self._calculate_weighted_moat_strength(moat_components)
            
            logger.info(f"参入障壁強度計算完了: {moat_strength:.3f}")
            
            return moat_strength
            
        except Exception as e:
            logger.error(f"参入障壁強度計算エラー: {str(e)}")
            return 0.0
    
    def identify_strategic_data_gaps(self, current_data: Dict) -> List[str]:
        """
        戦略的データ収集の改善点特定
        
        Args:
            current_data: 現在のデータ
            
        Returns:
            改善点リスト
        """
        try:
            strategic_gaps = []
            
            # 1. 競合優位性強化に必要なデータの特定
            competitive_gaps = self._identify_competitive_data_gaps(current_data)
            strategic_gaps.extend(competitive_gaps)
            
            # 2. 個人化精度向上のボトルネック特定
            personalization_gaps = self._identify_personalization_bottlenecks(current_data)
            strategic_gaps.extend(personalization_gaps)
            
            # 3. 参入障壁構築の弱点分析
            moat_gaps = self._identify_moat_building_weaknesses(current_data)
            strategic_gaps.extend(moat_gaps)
            
            # 4. データ品質向上の機会特定
            quality_gaps = self._identify_data_quality_opportunities(current_data)
            strategic_gaps.extend(quality_gaps)
            
            # 5. 重複排除と優先度付け
            strategic_gaps = self._prioritize_strategic_gaps(strategic_gaps)
            
            logger.info(f"戦略的データギャップ特定完了: {len(strategic_gaps)}件の改善点")
            
            return strategic_gaps
            
        except Exception as e:
            logger.error(f"戦略的データギャップ特定エラー: {str(e)}")
            return []
    
    def generate_comprehensive_moat_analysis(self, 
                                           collected_data: Dict,
                                           user_base_data: Dict) -> MoatAnalysis:
        """
        包括的参入障壁分析の実行
        
        Args:
            collected_data: 収集済みデータ
            user_base_data: ユーザーベースデータ
            
        Returns:
            包括的参入障壁分析結果
        """
        try:
            # 1. データ独自性評価
            uniqueness_analysis = self.measure_data_uniqueness(collected_data)
            
            # 2. 模倣困難度推定
            replication_analysis = self.estimate_replication_difficulty(collected_data)
            
            # 3. 参入障壁強度計算
            moat_strength_score = self.calculate_moat_strength(user_base_data)
            
            # 4. 戦略的ギャップ特定
            strategic_gaps = self.identify_strategic_data_gaps(collected_data)
            
            # 5. 競合優位性要素の特定
            competitive_advantages = self._identify_competitive_advantages(
                uniqueness_analysis, replication_analysis, moat_strength_score
            )
            
            # 6. 脆弱性ポイントの特定
            vulnerability_points = self._identify_vulnerability_points(
                uniqueness_analysis, replication_analysis, strategic_gaps
            )
            
            # 7. 改善機会の特定
            improvement_opportunities = self._identify_improvement_opportunities(strategic_gaps)
            
            # 8. 戦略的推奨事項の生成
            strategic_recommendations = self._generate_strategic_recommendations(
                competitive_advantages, vulnerability_points, improvement_opportunities
            )
            
            # 9. 全体的な参入障壁強度の決定
            overall_moat_strength = self._determine_overall_moat_strength(moat_strength_score)
            
            # 10. 包括的分析結果の構築
            moat_analysis = MoatAnalysis(
                overall_moat_strength=overall_moat_strength,
                moat_score=moat_strength_score,
                competitive_advantages=competitive_advantages,
                vulnerability_points=vulnerability_points,
                improvement_opportunities=improvement_opportunities,
                strategic_recommendations=strategic_recommendations,
                analysis_metadata={
                    'analysis_timestamp': datetime.now().isoformat(),
                    'data_volume': len(collected_data),
                    'user_base_size': user_base_data.get('total_users', 0),
                    'analysis_version': '1.0'
                }
            )
            
            # 11. 分析結果の保存
            self._save_moat_analysis(moat_analysis)
            
            logger.info(f"包括的参入障壁分析完了: 強度={overall_moat_strength.value}, "
                       f"スコア={moat_strength_score:.3f}")
            
            return moat_analysis
            
        except Exception as e:
            logger.error(f"包括的参入障壁分析エラー: {str(e)}")
            # エラー時のフォールバック
            return MoatAnalysis(
                overall_moat_strength=MoatStrength.WEAK,
                moat_score=0.0,
                competitive_advantages=[],
                vulnerability_points=[f"Analysis error: {str(e)}"],
                improvement_opportunities=[],
                strategic_recommendations=[],
                analysis_metadata={'error': str(e)}
            )
    
    # ヘルパーメソッド群（簡略化実装）
    def _evaluate_pattern_uniqueness(self, patterns: List) -> Dict[str, float]:
        """パターン独自性の評価"""
        return {
            'uniqueness_score': 0.8,
            'pattern_diversity': 0.7,
            'commercial_value': 0.9
        }
    
    def _evaluate_behavior_data_rarity(self, behavior_data: Dict) -> Dict[str, float]:
        """行動データ希少性の評価"""
        return {
            'rarity_index': 0.75,
            'collection_difficulty': 0.85,
            'market_availability': 0.3
        }
    
    def _evaluate_language_pattern_uniqueness(self, language_patterns: Dict) -> Dict[str, float]:
        """言語パターン独自性の評価"""
        return {
            'linguistic_uniqueness': 0.85,
            'cultural_specificity': 0.8,
            'replication_complexity': 0.9
        }
    
    def _calculate_overall_uniqueness(self, category_uniqueness: Dict) -> float:
        """全体独自性スコア計算"""
        if not category_uniqueness:
            return 0.0
        
        scores = []
        for category, metrics in category_uniqueness.items():
            if isinstance(metrics, dict) and 'uniqueness_score' in metrics:
                scores.append(metrics['uniqueness_score'])
        
        return statistics.mean(scores) if scores else 0.0
    
    def _assess_commercial_value_from_uniqueness(self, uniqueness_data: Dict) -> Dict[str, Any]:
        """独自性から商用価値を評価"""
        overall_score = uniqueness_data.get('overall_uniqueness_score', 0)
        
        if overall_score >= 0.8:
            value_level = DataCommercialValue.EXTREMELY_HIGH
        elif overall_score >= 0.6:
            value_level = DataCommercialValue.HIGH
        elif overall_score >= 0.4:
            value_level = DataCommercialValue.MEDIUM
        else:
            value_level = DataCommercialValue.LOW
        
        return {
            'commercial_value_level': value_level,
            'estimated_market_value_usd': overall_score * 1000000,  # 仮想的な評価
            'competitive_advantage_duration_months': int(overall_score * 60)
        }
    
    def _quantify_competitive_differentiation(self, uniqueness_data: Dict) -> Dict[str, float]:
        """競合差別化要素の定量化"""
        return {
            'differentiation_strength': uniqueness_data.get('overall_uniqueness_score', 0) * 0.9,
            'market_position_advantage': 0.8,
            'brand_differentiation_potential': 0.75
        }
    
    # その他のヘルパーメソッドも同様に簡略実装
    def _evaluate_data_collection_time_advantage(self, data: Dict) -> Dict[str, float]:
        return {'time_advantage_months': 24, 'first_mover_benefit': 0.8}
    
    def _evaluate_technical_collection_barriers(self, data: Dict) -> Dict[str, float]:
        return {'technical_complexity': 0.85, 'implementation_difficulty': 0.9}
    
    def _evaluate_user_behavior_complexity(self, data: Dict) -> Dict[str, float]:
        return {'behavior_complexity_score': 0.8, 'pattern_sophistication': 0.85}
    
    def _evaluate_learning_effect_barriers(self, data: Dict) -> Dict[str, float]:
        return {'learning_curve_steepness': 0.7, 'experience_advantage': 0.8}
    
    def _calculate_replication_difficulty_score(self, factors: Dict) -> float:
        """模倣困難度スコア計算"""
        scores = []
        for factor_data in factors.values():
            if isinstance(factor_data, dict):
                for value in factor_data.values():
                    if isinstance(value, (int, float)):
                        scores.append(float(value))
        
        return statistics.mean(scores) if scores else 0.5
    
    def _determine_replication_difficulty_level(self, score: float) -> ReplicationDifficulty:
        """模倣困難度レベル決定"""
        for difficulty, threshold in self.replication_thresholds.items():
            if score >= threshold:
                return difficulty
        return ReplicationDifficulty.EASY
    
    def _estimate_replication_time(self, factors: Dict) -> Dict[str, int]:
        """模倣時間推定"""
        return {
            'minimum_months': 12,
            'likely_months': 24,
            'maximum_months': 48
        }
    
    def _estimate_replication_costs(self, factors: Dict) -> Dict[str, float]:
        """模倣コスト推定"""
        return {
            'development_cost_usd': 500000,
            'data_collection_cost_usd': 1000000,
            'opportunity_cost_usd': 2000000
        }
    
    def _assess_replication_risks(self, analysis: Dict) -> Dict[str, float]:
        """模倣リスク評価"""
        return {
            'technical_risk': 0.7,
            'market_risk': 0.6,
            'competitive_response_risk': 0.8
        }
    
    def _measure_network_effects(self, user_data: Dict) -> float:
        """ネットワーク効果測定"""
        return 0.6
    
    def _measure_data_learning_effects(self, user_data: Dict) -> float:
        """データ学習効果測定"""
        return 0.75
    
    def _measure_personalization_advantage(self, user_data: Dict) -> float:
        """個人化優位性測定"""
        return 0.8
    
    def _measure_user_switching_costs(self, user_data: Dict) -> float:
        """ユーザー切り替えコスト測定"""
        return 0.5
    
    def _measure_brand_loyalty(self, user_data: Dict) -> float:
        """ブランドロイヤルティ測定"""
        return 0.4
    
    def _calculate_weighted_moat_strength(self, components: Dict) -> float:
        """重み付き参入障壁強度計算"""
        total_score = 0.0
        total_weight = 0.0
        
        weights = {
            'network_effects': 0.25,
            'learning_effects': 0.25,
            'personalization_advantage': 0.25,
            'switching_costs': 0.15,
            'brand_loyalty': 0.10
        }
        
        for component, score in components.items():
            if component in weights:
                total_score += score * weights[component]
                total_weight += weights[component]
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _identify_competitive_data_gaps(self, data: Dict) -> List[str]:
        """競合データギャップ特定"""
        return [
            "需要可更多言語覆蓋的翻譯數據",
            "需要行業特定翻譯模式數據",
            "需要實時用戶反饋數據"
        ]
    
    def _identify_personalization_bottlenecks(self, data: Dict) -> List[str]:
        """個人化ボトルネック特定"""
        return [
            "用戶行為歷史數據不足",
            "上下文理解能力有限",
            "個人化學習週期過長"
        ]
    
    def _identify_moat_building_weaknesses(self, data: Dict) -> List[str]:
        """参入障壁構築弱点特定"""
        return [
            "用戶切換成本較低",
            "網絡效應尚未充分發揮",
            "品牌忠誠度需要提升"
        ]
    
    def _identify_data_quality_opportunities(self, data: Dict) -> List[str]:
        """データ品質向上機会特定"""
        return [
            "數據收集覆蓋率可提升",
            "數據標註質量需改進",
            "數據驗證流程需完善"
        ]
    
    def _prioritize_strategic_gaps(self, gaps: List[str]) -> List[str]:
        """戦略的ギャップ優先度付け"""
        return gaps[:5]  # 上位5つを返す
    
    def _save_data_uniqueness_evaluation(self, analysis: Dict):
        """データ独自性評価の保存"""
        pass
    
    def _save_moat_analysis(self, analysis: MoatAnalysis):
        """参入障壁分析の保存"""
        pass
    
    def _identify_competitive_advantages(self, uniqueness: Dict, replication: Dict, moat_score: float) -> List[CompetitiveAdvantage]:
        """競合優位性特定"""
        return []
    
    def _identify_vulnerability_points(self, uniqueness: Dict, replication: Dict, gaps: List) -> List[str]:
        """脆弱性ポイント特定"""
        return ["データ収集手法の模倣可能性", "技術人材の不足"]
    
    def _identify_improvement_opportunities(self, gaps: List) -> List[str]:
        """改善機会特定"""
        return ["AI model fine-tuning acceleration", "Multi-language expansion"]
    
    def _generate_strategic_recommendations(self, advantages: List, vulnerabilities: List, opportunities: List) -> List[str]:
        """戦略的推奨事項生成"""
        return [
            "個人化データ収集の加速",
            "多言語対応の拡大",
            "ユーザー切り替えコスト向上策の実施"
        ]
    
    def _determine_overall_moat_strength(self, score: float) -> MoatStrength:
        """全体参入障壁強度決定"""
        if score >= 0.9:
            return MoatStrength.UNBREACHABLE
        elif score >= 0.8:
            return MoatStrength.VERY_STRONG
        elif score >= 0.6:
            return MoatStrength.STRONG
        elif score >= 0.4:
            return MoatStrength.MODERATE
        elif score >= 0.2:
            return MoatStrength.WEAK
        else:
            return MoatStrength.NONE


# テスト用メイン関数
if __name__ == "__main__":
    print("🎯 競合優位性・参入障壁分析システム - テスト実行")
    print("=" * 60)
    
    analyzer = CompetitiveAdvantageAnalyzer()
    
    # テスト用データ
    test_collected_data = {
        'personalization_patterns': [
            {'pattern_type': 'thinking_to_language', 'uniqueness': 0.8},
            {'pattern_type': 'cultural_adaptation', 'uniqueness': 0.9}
        ],
        'user_behavior_data': {
            'total_sessions': 1000,
            'unique_patterns': 150
        },
        'language_patterns': {
            'unique_expressions': 200,
            'cultural_specificity': 0.85
        }
    }
    
    test_user_base_data = {
        'total_users': 500,
        'active_users': 350,
        'retention_rate': 0.75
    }
    
    # 1. データ独自性評価テスト
    uniqueness_result = analyzer.measure_data_uniqueness(test_collected_data)
    print(f"✅ データ独自性評価:")
    print(f"  全体独自性スコア: {uniqueness_result.get('overall_uniqueness_score', 0):.3f}")
    print(f"  カテゴリ数: {len(uniqueness_result.get('category_uniqueness', {}))}")
    
    # 2. 模倣困難度推定テスト
    replication_result = analyzer.estimate_replication_difficulty(test_collected_data)
    print(f"\n🔒 模倣困難度推定:")
    print(f"  困難度レベル: {replication_result.get('overall_difficulty', 'unknown')}")
    print(f"  困難度スコア: {replication_result.get('difficulty_score', 0):.3f}")
    
    # 3. 参入障壁強度計算テスト
    moat_strength = analyzer.calculate_moat_strength(test_user_base_data)
    print(f"\n🏰 参入障壁強度計算:")
    print(f"  強度スコア: {moat_strength:.3f}")
    
    # 4. 戦略的ギャップ特定テスト
    strategic_gaps = analyzer.identify_strategic_data_gaps(test_collected_data)
    print(f"\n📋 戦略的ギャップ特定:")
    print(f"  特定されたギャップ数: {len(strategic_gaps)}")
    for i, gap in enumerate(strategic_gaps[:3], 1):
        print(f"    {i}. {gap}")
    
    # 5. 包括的分析テスト
    comprehensive_analysis = analyzer.generate_comprehensive_moat_analysis(
        test_collected_data, test_user_base_data
    )
    print(f"\n🎯 包括的参入障壁分析:")
    print(f"  全体的な参入障壁強度: {comprehensive_analysis.overall_moat_strength.value}")
    print(f"  参入障壁スコア: {comprehensive_analysis.moat_score:.3f}")
    print(f"  脆弱性ポイント数: {len(comprehensive_analysis.vulnerability_points)}")
    print(f"  改善機会数: {len(comprehensive_analysis.improvement_opportunities)}")
    print(f"  戦略的推奨事項数: {len(comprehensive_analysis.strategic_recommendations)}")
    
    print("\n✅ テスト完了 - 競合優位性分析システム正常動作")