
"""日志工具。

项目里很多步骤比较耗时，比如下载 embedding 模型、向量入库、rerank。
统一日志格式方便你在终端看到“现在程序跑到哪一步了”。
"""

import logging


def get_logger(name: str) -> logging.Logger:
    # basicConfig 只在首次调用时生效，多次 import 不会重复添加 handler。
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    return logging.getLogger(name)
