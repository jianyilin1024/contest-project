import next from "eslint-config-next/core-web-vitals";

/**
 * ESLint 扁平配置。
 * eslint-config-next v16 直接导出扁平配置数组，无需 FlatCompat。
 */
const config = [
  ...next,
  {
    ignores: [".next/**", "node_modules/**", "next-env.d.ts"],
  },
];

export default config;
