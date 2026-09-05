# Agent Backend / AI Application 面试算法与 Coding 手册

> 版本：2026-09-06，第二版。
>
> 目标岗位：Agent Backend、AI Application Engineer、大模型应用研发、LLM Application Engineer、AI 全栈偏后端、Data/Search/Knowledge Agent、Agent Runtime 初级岗位。
>
> 目标不是“刷题数量好看”，而是形成能通过笔试、手撕、后端追问、AI Coding 和项目深挖的一整套能力。

# 0. 先给结论：Hot 100 很重要，但绝对不是全部

对于本项目目标岗位，建议把面试准备看成 8 块：

```text
1. LeetCode Hot 100 主模式
2. Hot 100 外的公司高频补充
3. ACM 输入输出 / 限时笔试
4. SQL
5. Backend Coding 手撕
6. CS 基础八股
7. System Design
8. RAG / Agent / AI Coding + 项目深挖
```

如果只刷 Hot 100，你会缺：

- SQL
- Redis / MySQL / 网络 / OS
- LRU 之外的工程组件
- 限流 / retry / timeout / queue
- SSE / FastAPI
- Tool Calling / Agent loop
- System Design
- Agent/RAG 项目追问

如果完全不刷算法，只会讲 Agent 项目，也容易在第一轮手撕直接挂掉。

因此最合理策略是：

> **Hot100 打底 + 高频补充 + 工程手撕 + AI Coding。**

---

# 1. 如何使用这份文档

不要按 LeetCode 页面随机刷。

每个题型都走：

```text
识别信号
→ 核心不变量/思路
→ 最小模板
→ 代表题
→ 不看答案重写
→ 复杂度
→ 变化题
→ 工程迁移
```

一道题只有达到下面标准才算“会”：

- 看到题能判断大类。
- 先口述方案再写代码。
- 不看答案从空白编辑器写出。
- 能解释时间/空间复杂度。
- 能主动测 2–3 个边界。
- 一周后还能重写。
- 面试官改一个条件时能继续推。

建议状态：

- `A`：完全不会
- `B`：看解析能理解
- `C`：当天可独立写
- `D`：一周后可独立写 + 能讲变化

真正面试目标是 P0 题大部分达到 `D`。

---

# 2. 推荐训练顺序

## Phase 1：基础模式

1. Array / Hash
2. Two Pointers
3. Sliding Window
4. Prefix Sum
5. Linked List
6. Stack / Queue

## Phase 2：树、堆、二分

7. Binary Tree / BST
8. Heap / TopK
9. Binary Search

## Phase 3：图与搜索

10. DFS / BFS
11. Topological Sort
12. Union Find
13. Backtracking

## Phase 4：高级高频

14. Greedy
15. Dynamic Programming
16. Interval
17. Monotonic Stack / Queue
18. Trie / LRU

## Phase 5：公司补充

19. Sorting
20. Shortest Path
21. Bit Manipulation
22. Difference Array
23. String basics
24. ACM I/O

## Phase 6：工程面试

25. SQL
26. Backend hand-coding
27. CS fundamentals
28. System Design

## Phase 7：AI Coding

29. FastAPI
30. SSE
31. Tool Calling
32. Simple RAG
33. Agent State
34. Reliability / Eval

---

# Part A：LeetCode 主干题单

# 3. Array / Hash

识别信号：

- 是否出现过
- 次数统计
- 去重
- 两数关系
- 分组
- O(1) 成员查找

## P0

- 1 Two Sum
- 49 Group Anagrams
- 128 Longest Consecutive Sequence
- 217 Contains Duplicate
- 242 Valid Anagram

## P1

- 347 Top K Frequent Elements
- 36 Valid Sudoku
- 238 Product of Array Except Self

核心：Python `dict` / `set` 平均查找 O(1)，不是数学意义上的任何情况下恒定 O(1)。

最小模式：

```python
seen = {}
for i, x in enumerate(nums):
    if target - x in seen:
        return [seen[target - x], i]
    seen[x] = i
```

工程迁移：cache key、dedup、idempotency key、frequency counter。

---

# 4. Two Pointers

识别信号：

- 有序数组
- 两端往中间
- 原地去重/移动
- 快慢指针

## P0

- 283 Move Zeroes
- 11 Container With Most Water
- 15 3Sum
- 125 Valid Palindrome

## P1

- 167 Two Sum II
- 42 Trapping Rain Water

核心问题：**为什么移动这一边能排除一批答案？**

---

# 5. Sliding Window

识别信号：

- 连续子数组 / 子串
- 最长 / 最短
- 最近 N 个 / N 秒
- 窗口内满足约束

## P0

- 3 Longest Substring Without Repeating Characters
- 438 Find All Anagrams in a String
- 209 Minimum Size Subarray Sum

## P1

- 76 Minimum Window Substring
- 239 Sliding Window Maximum
- 424 Longest Repeating Character Replacement

通用框架：

```python
left = 0
for right, x in enumerate(data):
    add(x)
    while invalid():
        remove(data[left])
        left += 1
    update_answer(left, right)
```

必须能回答：

- 为什么是 `while` 而不是 `if`？
- 什么情况下答案在收缩前更新？
- 窗口状态如何 O(1) 更新？

工程迁移：sliding-window rate limiter。

---

# 6. Prefix Sum / Difference

识别信号：

- 区间和
- 连续子数组统计
- 多次区间查询
- 多次区间加减

## P0

- 560 Subarray Sum Equals K
- 724 Find Pivot Index

## P1

- 304 Range Sum Query 2D
- 525 Contiguous Array
- 1109 Corporate Flight Bookings（差分）

重要：存在负数时，很多“和等于 K”问题不能简单用滑动窗口。

工程迁移：时间区间统计、批量配置变更、监控指标区间累积。

---

# 7. Linked List

## P0

- 206 Reverse Linked List
- 21 Merge Two Sorted Lists
- 141 Linked List Cycle
- 160 Intersection of Two Linked Lists
- 19 Remove Nth Node From End
- 2 Add Two Numbers

## P1

- 24 Swap Nodes in Pairs
- 25 Reverse Nodes in K-Group
- 138 Copy List with Random Pointer

习惯：删除/插入头部时优先考虑 dummy node。

必须会解释：

- random access 为什么 O(n)
- 已知节点位置时插删为什么可 O(1)
- 链表与数组的 cache locality 区别

---

# 8. Stack / Queue / Monotonic Structure

## P0

- 20 Valid Parentheses
- 155 Min Stack
- 739 Daily Temperatures
- 394 Decode String

## P1

- 84 Largest Rectangle in Histogram
- 239 Sliding Window Maximum
- 402 Remove K Digits

单调栈信号：

> 对每个元素找左/右第一个更大/更小。

单调队列信号：

> 滑动窗口不断求 max/min。

---

# 9. Binary Tree / BST

树必须非常稳，因为它能同时考递归、DFS、BFS、栈、队列。

## P0

- 94 Binary Tree Inorder Traversal
- 102 Binary Tree Level Order Traversal
- 104 Maximum Depth of Binary Tree
- 226 Invert Binary Tree
- 543 Diameter of Binary Tree
- 98 Validate Binary Search Tree
- 230 Kth Smallest Element in a BST
- 236 Lowest Common Ancestor of a Binary Tree
- 105 Construct Binary Tree from Preorder and Inorder

## P1

- 199 Binary Tree Right Side View
- 124 Binary Tree Maximum Path Sum
- 297 Serialize and Deserialize Binary Tree

递归三问：

1. 当前函数定义是什么？
2. 子问题返回什么？
3. 当前节点如何组合子问题？

先理解递归，再补 iterative stack 版本。

---

# 10. Heap / Priority Queue / TopK

## P0

- 215 Kth Largest Element in an Array
- 347 Top K Frequent Elements
- 23 Merge K Sorted Lists

## P1

- 295 Find Median from Data Stream
- 703 Kth Largest in a Stream
- 621 Task Scheduler

Python `heapq` 默认最小堆。

要能解释：

- push/pop O(log n)
- peek O(1)
- TopK 为什么常用大小 K 的小顶堆

工程迁移：priority job queue、scheduler、top slow requests。

---

# 11. Binary Search

必须会三类：

1. exact search
2. lower/upper bound
3. binary search on answer

## P0

- 704 Binary Search
- 33 Search in Rotated Sorted Array
- 34 Find First and Last Position
- 153 Find Minimum in Rotated Sorted Array

## P1

- 875 Koko Eating Bananas
- 1011 Capacity To Ship Packages Within D Days

固定一种边界写法，不要临场 `[l,r]` 与 `[l,r)` 混用。

---

# 12. Graph DFS / BFS

## P0

- 200 Number of Islands
- 994 Rotting Oranges
- 133 Clone Graph
- 207 Course Schedule

## P1

- 127 Word Ladder
- 417 Pacific Atlantic Water Flow
- 399 Evaluate Division

BFS 天然适合无权最短步数；DFS 常用于连通块/遍历。

---

# 13. Topological Sort

Agent 后端/工作流岗位很值得补。

## P0

- 207 Course Schedule
- 210 Course Schedule II

Kahn：

```python
from collections import deque


def topo(n, edges):
    graph = [[] for _ in range(n)]
    indegree = [0] * n
    for a, b in edges:
        graph[a].append(b)
        indegree[b] += 1

    q = deque(i for i in range(n) if indegree[i] == 0)
    order = []
    while q:
        x = q.popleft()
        order.append(x)
        for y in graph[x]:
            indegree[y] -= 1
            if indegree[y] == 0:
                q.append(y)
    return order if len(order) == n else []
```

工程迁移：workflow DAG、job dependencies。

---

# 14. Union Find

## P1

- 547 Number of Provinces
- 684 Redundant Connection
- 721 Accounts Merge

必须理解：

- parent
- path compression
- union by size/rank

工程迁移：cluster membership、connected components、account merge。

---

# 15. Backtracking

## P0

- 46 Permutations
- 78 Subsets
- 39 Combination Sum
- 22 Generate Parentheses
- 79 Word Search

## P1

- 51 N-Queens
- 17 Letter Combinations of a Phone Number

结构：

```text
选择
→ 递归
→ 撤销
```

必须能分清：组合题是否允许重复、是否需要 start index、是否需要去重。

---

# 16. Greedy / Interval

## P0

- 55 Jump Game
- 121 Best Time to Buy and Sell Stock
- 56 Merge Intervals
- 763 Partition Labels
- 435 Non-overlapping Intervals

## P1

- 45 Jump Game II
- 452 Minimum Number of Arrows

贪心不能只背代码；要能说明为什么当前局部选择不会破坏未来最优。

---

# 17. Dynamic Programming

学习顺序：

```text
一维
→ 网格
→ 背包
→ 子序列
→ 状态机
```

四问：

1. `dp[i]` / `dp[i][j]` 表示什么？
2. 从哪些状态转移？
3. base case？
4. 遍历顺序为什么？

## P0

- 70 Climbing Stairs
- 198 House Robber
- 322 Coin Change
- 300 Longest Increasing Subsequence
- 1143 Longest Common Subsequence
- 72 Edit Distance
- 62 Unique Paths
- 64 Minimum Path Sum

## P1

- 416 Partition Equal Subset Sum
- 494 Target Sum
- 139 Word Break
- 309 Best Time to Buy and Sell Stock with Cooldown
- 123 / 188 Stock 系列进阶

先写直观二维状态，再考虑空间压缩。

---

# 18. Trie / LRU / LFU

## Trie

- 208 Implement Trie
- 211 Design Add and Search Words

适用：prefix、dictionary、route matching。

## LRU — P0 必会手写

- 146 LRU Cache

目标：`get/put` O(1)。

经典：

```text
HashMap + Doubly Linked List
```

面试中不要只用 `OrderedDict` 一行带过；至少会手写节点和移动逻辑。

## LFU — P2

- 460 LFU Cache

理解 frequency + recency 即可，不是所有目标岗必做。

---

# Part B：Hot100 外高频补充

# 19. Sorting

至少能从空白写：

- Quick Sort
- Merge Sort

理解：

- Heap Sort
- stable / unstable
- in-place

| 算法 | 平均 | 最坏 | 空间 | 稳定 |
|---|---:|---:|---:|---|
| Quick Sort | O(n log n) | O(n²) | recursion | 否 |
| Merge Sort | O(n log n) | O(n log n) | O(n) | 是 |
| Heap Sort | O(n log n) | O(n log n) | O(1) 级 | 否 |

公司面试仍可能直接让你手写排序，不要因为 Python 有 `sort()` 就跳过。

---

# 20. Shortest Path

P1/P2：

- BFS：unweighted
- Dijkstra：non-negative weighted graph
- Bellman-Ford：知道适用边界

代表题：

- 743 Network Delay Time
- 787 Cheapest Flights Within K Stops

Agent Backend 工程中更重要的是理解 scheduler/dependency graph，不要求每个岗位都手写 Floyd。

---

# 21. Bit / String / Misc

P1：

- 136 Single Number
- 191 Number of 1 Bits
- 338 Counting Bits
- 31 Next Permutation
- 54 Spiral Matrix
- 48 Rotate Image

字符串算法：普通目标岗先掌握 Hash / sliding window / trie；KMP 知道原理和 prefix function 即可，除非公司笔试明显高频。

---

# Part C：ACM / 笔试输入输出

# 22. 为什么要练 ACM

LeetCode 帮你处理输入输出，真实笔试常不会。

你至少要熟悉：

```python
import sys

nums = list(map(int, sys.stdin.readline().split()))
```

多组数据：

```python
import sys

it = iter(sys.stdin.read().strip().split())
t = int(next(it))
for _ in range(t):
    n = int(next(it))
    arr = [int(next(it)) for _ in range(n)]
    print(sum(arr))
```

训练目标：

- 读清多组输入
- 处理空格/换行
- 不依赖 IDE 交互
- 控制复杂度
- 自己构造边界样例

每周至少做一次 60–90 分钟组合笔试。

---

# Part D：SQL

# 23. SQL 必会层级

## P0 语法

- SELECT / WHERE
- ORDER BY / LIMIT
- INNER JOIN / LEFT JOIN
- GROUP BY / HAVING
- CASE WHEN
- subquery / CTE

## P0 Window Functions

必须分清：

- ROW_NUMBER
- RANK
- DENSE_RANK
- SUM/AVG OVER
- PARTITION BY

代表练习：

- 175 Combine Two Tables
- 181 Employees Earning More Than Managers
- 182 Duplicate Emails
- 184 Department Highest Salary
- 185 Department Top Three Salaries
- 178 Rank Scores
- 180 Consecutive Numbers

## P1 Backend 数据库知识

- B+ Tree
- clustered / secondary index
- covering index
- leftmost prefix
- back-to-table
- EXPLAIN
- ACID
- isolation levels
- MVCC
- deadlock
- slow query
- pagination

练习时不要只追求 SQL 输出正确；还要问“数据量变大后索引怎么建”。

---

# Part E：Backend Coding 手撕

# 24. 必练组件

这些不是普通 Hot100，却非常适合 Agent Backend 面试。

## P0

1. LRU Cache
2. thread-safe queue
3. producer-consumer
4. sliding-window rate limiter
5. token bucket
6. retry with exponential backoff + jitter
7. timeout wrapper
8. TTL cache
9. concurrency semaphore
10. idempotent request handler
11. SSE endpoint
12. simple task state machine

## P1

13. connection pool 思路
14. distributed lock 思路
15. simple delayed/retry queue
16. task scheduler / priority queue
17. circuit breaker
18. cache-aside

## 24.1 Sliding-window limiter

```python
from collections import deque
from time import monotonic


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float):
        self.limit = limit
        self.window = window_seconds
        self.events = deque()

    def allow(self) -> bool:
        now = monotonic()
        cutoff = now - self.window
        while self.events and self.events[0] <= cutoff:
            self.events.popleft()
        if len(self.events) >= self.limit:
            return False
        self.events.append(now)
        return True
```

然后继续追问：

- thread safe 吗？
- multi-process 呢？
- distributed 呢？
- 为什么生产环境可能放 Redis？
- fixed/sliding/token bucket 如何选择？

## 24.2 Retry

必须讲清：

- retryable vs non-retryable
- 401 通常不盲重试
- 429/5xx
- exponential backoff
- jitter
- retry budget
- idempotency

## 24.3 Task state machine

至少能设计：

```text
queued
→ running
→ succeeded
→ failed
→ retrying
→ cancelled
```

这直接连接本项目未来 durable task Roadmap。

---

# Part F：CS 基础

# 25. Network

必须能讲：

- TCP vs UDP
- three-way handshake
- four-way close
- TCP reliability
- HTTP/1.1 vs HTTP/2 基础
- HTTPS/TLS 基础
- keep-alive
- REST
- SSE vs WebSocket
- reverse proxy / gateway
- 401/403/429/500/502/503/504
- timeout 分层

Agent 场景迁移：LLM streaming、tool timeout、gateway、client disconnect。

---

# 26. OS / Concurrency

必须能讲：

- process vs thread
- context switch
- lock / race / deadlock
- thread pool
- producer-consumer
- IO multiplexing
- sync vs async
- Python GIL
- async vs thread vs process
- cancellation
- backpressure 基础

不要说“async 更快”；要说它适合 I/O wait 并提高并发利用率。

---

# 27. Redis

必须会：

- String / Hash / List / Set / ZSet
- expiration
- eviction
- persistence
- cache penetration
- cache breakdown
- cache avalanche
- hot key / big key
- distributed lock 基础
- Redis/MySQL consistency

结合 Agent：session/cache/rate-limit/ephemeral state。

---

# 28. MQ / Distributed Basics

必须会：

- why queue
- producer retry
- consumer retry
- duplicate delivery
- idempotency
- ordering
- message loss
- dead/retry queue
- eventual consistency
- worker lease/heartbeat 基础

结合 Agent：long-running task、tool workflow、background execution。

---

# Part G：System Design

# 29. 必会设计题：企业 Agent Backend

题目：

> 设计一个支持 RAG、工具调用、流式输出、长任务和失败恢复的企业 Agent 服务。

建议层次：

1. API / Gateway：auth、rate limit、request ID
2. Session / State：conversation、checkpoint
3. Orchestrator：workflow / agent loop
4. Tool Layer：registry、schema、permission、timeout
5. RAG：retrieve、rerank、context、citation
6. Model Layer：routing、fallback
7. Async Jobs：queue、worker、durable state
8. Storage：Postgres / Redis / vector store
9. Safety：permission、sandbox、HITL
10. Observability：trace、logs、metrics、token/cost
11. Eval：offline regression、online feedback

追问必须准备：

- 服务重启怎么办？
- 工具执行一半崩了怎么办？
- duplicate request 怎么办？
- 用户断开 SSE 怎么办？
- 哪些状态放 Redis、哪些放 Postgres？
- 多租户怎么隔离？
- tool 权限怎么控制？
- 如何判断 Agent 版本真的更好？

面试官更看重 failure mode 和 trade-off，不是你画了多少微服务方框。

---

# Part H：AI Coding

# 30. 30–60 分钟必须能写的小任务

## Task 1：FastAPI LLM endpoint

要求：

- Pydantic request/response
- input validation
- timeout
- exception mapping
- secret 不回传

## Task 2：SSE stream

要求：

- correct content type
- client disconnect
- cancellation
- error event

## Task 3：Tool Calling loop

要求：

- tool schema
- registry
- argument validation
- dispatch
- timeout
- error taxonomy
- observation
- max steps
- final answer

本项目对应：

- `src/rag_agent/agent/tooling.py`
- `scripts/tool_agent.py`
- `tests/test_tooling.py`

## Task 4：Simple RAG

要求：

```text
chunk
→ retrieve
→ top-k
→ context
→ generation
→ citation
→ no-evidence refusal
```

## Task 5：Conversation / Agent State

要求：

- thread/session ID
- message state
- checkpoint
- concurrent request conflict
- short-term state vs long-term memory

## Task 6：Reliability

故意制造：

- timeout
- invalid JSON
- unknown tool
- 429
- 500
- empty result

系统必须分类，不能全叫“模型错误”。

## Task 7：Agent Eval

固定一批任务，记录：

- task success
- correct tool
- valid arguments
- tool success
- recovery
- step count
- latency
- token/cost

---

# Part I：项目深挖

# 31. 这个仓库就是面试训练场

- `src/rag_agent/retrieval/fusion.py`：排名/融合
- `src/rag_agent/retrieval/hybrid.py`：Hash、集合、TopK、多路结果
- `src/rag_agent/agent/graph.py`：state machine、bounded loop
- `src/rag_agent/agent/tooling.py`：registry、validation、failure taxonomy
- `src/rag_agent/api/main.py`：FastAPI/SSE/request lifecycle
- `src/rag_agent/api/jobs.py`：为什么内存 JobRegistry 不是 durable queue
- `src/rag_agent/retrieval/sqlite_store.py`：SQL/索引
- `tests/`：边界条件和 regression

每学一个主题都问：

> 这个项目里有真实实现吗？代码在哪？如果没有，应该实现还是只需要学习？

---

# 32. 高频项目追问

必须能回答：

- 为什么 dense + sparse？
- RRF 为什么不直接加原分数？
- reranker 提升什么、增加什么成本？
- evidence gate 怎么失败？
- citation validation 能保证事实真实吗？
- 为什么要拒答？
- checkpoint 与 long-term memory 区别？
- MCP 与 Tool Calling 区别？
- Tool Registry 为什么需要？
- unknown tool 为什么绝不能直接执行？
- retry 哪些错误能做？
- 为什么现在的 JobRegistry 不能叫 durable execution？
- Agent Eval 和普通 unit test 有什么区别？
- 为什么不是上来就 Multi-Agent？

---

# Part J：完整训练计划

# 33. 12 周路线

每周根据课程/申请安排可压缩，但顺序不要乱。

## Week 1

Array/Hash + Two Pointers

目标：10–12 题，P0 能复写。

## Week 2

Sliding Window + Prefix Sum + Linked List

额外：手写 sliding-window limiter。

## Week 3

Stack/Queue + Tree

额外：BFS/DFS 口述。

## Week 4

Heap + Binary Search

额外：TopK 工程场景。

## Week 5

Graph + Topo + Union Find

额外：设计简单 workflow DAG。

## Week 6

Backtracking + Greedy + Interval

开始 45 分钟双题限时。

## Week 7

DP

不要追难题，先把状态定义写清楚。

## Week 8

Trie + LRU + Sorting + ACM I/O

LRU 必须空白手写。

## Week 9

SQL + MySQL/Redis

窗口函数、索引、事务。

## Week 10

Network + OS + concurrency + MQ

手写 queue/retry/timeout。

## Week 11

FastAPI + SSE + Tool Calling + Simple RAG

做 2 次 60 分钟 AI Coding 模拟。

## Week 12

System Design + 项目深挖 + 综合模拟

一场模拟至少包含：

- 1 算法题
- 1 SQL/Backend 问题
- 1 Agent/RAG 项目追问
- 1 System Design

---

# 34. 日常最小训练法

如果每天只有 60–90 分钟：

```text
20 min：复写旧题
30 min：新题/变化题
20 min：Backend/SQL/CS
10 min：口述项目一个模块
```

如果当天完全没时间：只复写 1 个 P0 模板，也比连续一周断掉好。

---

# 35. 周末检查

每周随机抽：

- 2 道本周 P0
- 1 道上两周旧题
- 1 个 Backend component
- 1 组 SQL
- 1 个 Agent 项目问题

全部不看答案。

如果旧题写不出，把状态从 D/C 降回 B，不自欺欺人。

---

# 36. 公司笔试/面试证据如何反向更新题单

根目录 `AGENTS.md` 要求每次接手都重新扫招聘市场。

算法文档也遵循同样规则：

```text
新面经/笔试证据
→ 记录题型
→ 判断是否多家公司重复
→ 提升/降低 P0/P1
→ 不因单个极端难题无限扩张题库
```

当前 2026 Agent/后端面经反复出现的方向包括：

- sliding window
- LRU
- tree / graph / topo
- sorting
- DP
- Redis / DB
- concurrency
- SSE / MCP / Agent
- rate limiter / cache / queue 这类工程手撕

因此 Hot100 保留主干，同时加入 Backend Coding 才符合目标岗位。

---

# 37. 最低面试完成标准

## Algorithms

- P0 模式大部分达到 D。
- 中等题能在 20–30 分钟给出可运行方案。
- 能处理边界和复杂度。

## SQL

- Join / Group / Window / TopN 能现场写。
- 索引/事务/MVCC 能解释。

## Backend

- LRU / limiter / retry / timeout / queue 至少 4 个能手写或完整设计。
- Redis/MySQL/MQ/HTTP/SSE/concurrency 不只会名词。

## AI Coding

能独立做：

```text
FastAPI
+ Tool/RAG
+ validation
+ timeout/error
+ state
```

的最小程序。

## Project

能从：

```text
problem
→ architecture
→ code path
→ failure
→ test
→ metric
→ trade-off
→ roadmap
```

完整讲下来。

## System Design

能设计 Agent service，并说明为什么当前项目没有必要把所有东西都做成 Kubernetes 分布式平台。

---

# 38. 你不需要为了“全面”刷什么

对 Agent Backend / AI Application 初级岗位，暂时不用把主要时间投入：

- 竞赛级数学
- 极难网络流
- 冷门高级字符串算法大全
- 复杂计算几何
- 大量 Hard 题打卡

除非目标公司的笔试证据明确要求。

更高收益的是：

> **稳定写出常见 Medium + 后端基础 + Agent 项目 + AI Coding。**

---

# 39. 最后记住

Hot100 不是目的。

真正目标是让你看到一个新问题时能判断：

- 这是 Hash 还是 window？
- 这是 BFS 还是 topo？
- 这是算法问题还是系统状态问题？
- timeout 后能不能 retry？
- 是否需要幂等？
- state 应该放哪里？
- Agent 失败如何测？

当算法、后端和 Agent 能用同一套问题拆解方式解释时，这份训练才真正完成。