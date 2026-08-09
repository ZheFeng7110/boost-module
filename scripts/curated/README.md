# curated/ — generator blind-spot overrides

兜底清单目录 (计划: `scripts/curated/<mod>.txt`)。gen_exports.py 生成器看不见的
实体 (宏生成、GMF 全局辅助实体等) 由此处的每行一个限定名补入导出列表:

- `boost::foo::bar` — 在 `boost::foo` 命名空间块内输出 `using boost::foo::bar;`
- `::operator new` — 全局作用域实体, 输出 `export using ::operator new;`
  (M0 坑 A: gcc 的 GMF 全局辅助实体需显式再导出, 如 container 的 placement_new)

当前 27 个目标库均未触发 (M0 已知的 container 坑不在目标集内); M3 遇到
编译器实现缺口时在此登记并同步 gen_exports.py 读取逻辑 (尚未实现读取, 需要时加)。
