# 数据格式规范

按明确的profile提供Schema，校验对应输入字段和结构。当前rpglab-ieee24-native.schema.json只针对已验证的IEEE24原模型profile，不是适用于所有UC模型的通用Schema。

新增无网络、含网络、随机、水电或储能算例时，先判断能否无损复用已有profile；不支持的字段/模型语义应新增或版本化profile及Schema，并更新catalog中的profile/schema_version，不以删除约束或补造数值强行匹配。

Schema通过仅表示符合格式及该Schema声明的条件，不证明UC可行、最优或N-1安全。
