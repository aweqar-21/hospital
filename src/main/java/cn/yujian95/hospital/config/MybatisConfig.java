package cn.yujian95.hospital.config;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.context.annotation.Configuration;

/**
 * Mybatis 配置类
 *
 * @author AWEQAR_21 aweqar1225918785@gmail.com
 * @date 2020/1/19
 */

@MapperScan("cn.yujian95.hospital.mapper")
@Configuration
public class MybatisConfig {
}
