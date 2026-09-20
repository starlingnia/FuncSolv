target("FuncSolv")
    set_kind("binary")
    set_languages("c++26")
    
    -- 自动扫描 src 及 src/tasks 下的 cpp 文件
    add_rules("mode.debug", "mode.release")
    
    -- 首次构建时自动重命名占位目录至 Pitchfork 标准目录
    on_load(function (target)
        local dummy_dir = "include/__PROJECT_NAME__"
        local real_dir  = "include/" .. target:name()
        os.mkdir(path.join(os.projectdir(), "bin/"))       
        os.mkdir(path.join(os.projectdir(), "src/"))
        os.mkdir(path.join(os.projectdir(), "docs/"))
        os.mkdir(path.join(os.projectdir(), "tools/"))
         
        if os.isdir(dummy_dir) then
            os.mv(dummy_dir, real_dir)
            print("✨ Auto-renamed include directory to Pitchfork standard: " .. real_dir)
        end
    end)
    
    add_includedirs("include")
