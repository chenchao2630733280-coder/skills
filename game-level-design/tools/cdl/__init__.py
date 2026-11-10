"""cdl —— 休闲游戏难度自动化设计工具包（Casual Difficulty Lab）。

纯标准库实现，包含：
- schema   关卡战役配置的加载、校验与特征派生
- score    多维特征 -> 难度分/子分
- mapping  难度分 <-> 通关率（玩家分层的能力模型）
- curve    目标难度曲线生成
- jump     相邻关卡难度跳变检测
- sim      玩家表现蒙特卡洛模拟（替代模拟，不是真实玩家）
- actuals  真实通关数据聚合
- diagnose 异常关卡与卡点识别
- recommend 参数反向推荐
- report   评审报告与门禁
"""

__version__ = "3.0.0"
