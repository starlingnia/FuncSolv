add_rules("mode.debug", "mode.release")

-- ==============================================================================
-- 核心静态库 (原子计算核心与 IOdata 组件)
-- ==============================================================================
target("FuncSolv_core")
    set_kind("static")
    set_languages("c++26")
    add_includedirs("include")
    add_files("src/MergeSortedLists/*.cpp")
    add_files("src/WaterVolume/*.cpp")
    add_files("src/IOdata/*.cpp")
    set_targetdir("lib")

-- ==============================================================================
-- 任务组件 (单独只编译出 .o 目标文件，通过注册表挂载供 CLI 主程序调用)
-- ==============================================================================
target("FuncSolv_tasks")
    set_kind("object")
    set_languages("c++26")
    add_includedirs("include")
    add_files("build/*_task.cpp")
    add_deps("FuncSolv_core")

-- ==============================================================================
-- 共享动态库 (统一输出至 lib/，严禁污染 build/)
-- 暴露 C-ABI 供 Python ctypes 加载调用
-- ==============================================================================
target("formergesortlists")
    set_kind("shared")
    set_languages("c++26")
    set_basename("formergesortlists")
    add_includedirs("include")
    add_files("tools/Services/*.cpp")
    add_deps("FuncSolv_core")
    set_targetdir("lib")

-- ==============================================================================
-- 原生 CLI 驱动主程序 (包含 apps/ 下驱动主程序与 build/ 下注册的任务组件)
-- ==============================================================================
target("FuncSolv")
    set_kind("binary")
    set_languages("c++26")
    add_includedirs("include")
    add_files("apps/*.cpp")
    add_deps("FuncSolv_tasks", "FuncSolv_core")
    set_targetdir("bin")

    -- 补齐 Pitchfork 标准目录
    on_load(function (target)
        local dirs = {
            "bin", "lib", "build", "src", "src/MergeSortedLists", "src/WaterVolume", "src/IOdata",
            "docs", "tools", "tools/Services", "opt", "include/core",
            "scripts", "data", "output"
        }
        for _, dir in ipairs(dirs) do
            local p = path.join(os.projectdir(), dir)
            if not os.isdir(p) then
                os.mkdir(p)
            end
        end
    end)
