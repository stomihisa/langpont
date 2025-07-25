#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
デバッグ実行スクリプト
"""

import os
import sys

# 現在のディレクトリをlangpontに設定
os.chdir('/Users/shintaro_imac_2/langpont')

# debug_database.pyをインポートして実行
from debug_database import investigate_database

if __name__ == "__main__":
    investigate_database()