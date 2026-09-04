# Hospital 作者元数据迁移设计

## 目标

将当前项目文件中遗留的个人作者标注统一为项目维护者身份：

- 名称：`AWEQAR_21`
- 邮箱：`aweqar1225918785@gmail.com`
- 项目主页：`https://github.com/aweqar-21/hospital`

## 修改范围

- 将 Java 源码注释中的旧 `@author` 名称和邮箱统一替换为新身份。
- 将 Python `pyproject.toml` 的作者元数据改为新身份。
- 将 Maven 项目主页改为新的 GitHub 仓库地址。
- 将本仓库的本地 Git 提交身份设置为新名称和邮箱，使后续提交使用新身份。
- 检查 README、配置和其他当前文件，删除旧作者邮箱及旧个人主页引用。

## 明确不修改

- 不重写任何已有 Git 提交的 author/committer，保留真实提交历史。
- 不强推 GitHub 或 Gitee。
- 不修改 Java 包名、目录、import 或 Maven `groupId` 中的 `cn.yujian95.hospital`，避免破坏 Spring、MyBatis 和客户端兼容性。
- 不删除许可证或伪造第三方贡献归属。

## 验证与发布

- 添加或执行元数据契约检查，确保当前受控文件中不再出现旧作者邮箱、旧博客和旧 `@author` 标注。
- 运行 Java 全量测试与打包，确认纯元数据修改没有影响构建。
- 检查 Git 提交作者为新身份。
- 以普通提交分别更新 GitHub 和 Gitee，禁止 force push。

