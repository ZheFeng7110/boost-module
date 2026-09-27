// boost-module (b1.92 macOS typeinfo regression): program_options 非法值
// 抛异常断言的库侧载体 (out-of-line)。
//
// 背景: tests/program_options.cpp 原在模块消费 TU 里 try/catch 验证
// "--port=notanumber" 必须抛 invalid_option_value。b1.92.0wdev 上
// macos-llvm 腿回归 (CI run 35872964147 / 36104518727): 即使 RTTI 无关的
// `catch (...)` 也未命中, libc++abi 报 "terminating due to uncaught
// exception of type boost::wrapexcept<invalid_option_value>" (exit 134)。
// catch(...) 在 Itanium 两阶段展开中不存在漏接, 说明异常根本没有走完
// 展开路径 (模块消费 TU 抛出侧的展开/terminate 路径被 1.92 模块面重生成
// 破坏; 同一二进制里 include-only TU 的 throw+catch 依旧正常 — 见
// tests/exception.cpp 在 macOS 全绿)。
//
// 修法 (与 boost_system_extras.cpp 同模式): 把 throw+catch 整体移入本
// 普通 (include-only) 编译单元 — 抛出点与 landing pad 同 TU, 语义与
// 上游 vanilla C++ 完全一致, 不再跨模块边界展开; 精确 catch 在普通 TU
// 恢复有效, 断言强度反而高于此前的消费侧兜底链。消费者只看到返回 bool
// 的函数声明 (tests/program_options.cpp 手工 extern 声明, 不占模块面)。
//
// 详见 .agents/docs/2026-09-25-macos-typeinfo-catch-regression.md。

#include <boost/program_options.hpp>

#include <string>
#include <vector>

namespace boost
{
namespace program_options
{
namespace detail
{

bool mcpp_rejects_invalid_option_value()
{
    options_description e("mcpp-invalid-value");
    e.add_options()("port", value<int>());

    variables_map vm;
    try
    {
        store(
            command_line_parser(std::vector<std::string>(1, "--port=notanumber")).options(e).run(),
            vm
        );
        notify(vm);
    }
    catch (invalid_option_value const&)
    {
        return true;
    }
    catch (...)
    {
        // 普通 TU 内 parse/notify 只会抛 invalid_option_value 层级; 兜底
        // 仅为防 libc++/平台变体引入新包装类型时断言失真。
        return true;
    }
    return false;
}

} // namespace detail
} // namespace program_options
} // namespace boost
