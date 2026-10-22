# 前端镜像：deps -> build -> runner（Next.js standalone）
#
# NPM_REGISTRY 可通过构建参数覆盖：国内服务器建议设为 https://registry.npmmirror.com

FROM node:22-alpine AS base
ARG NPM_REGISTRY=https://registry.npmjs.org
# corepack 下载 pnpm 走的是自己的变量，pnpm 读 ~/.npmrc，两处都要设
ENV COREPACK_NPM_REGISTRY=${NPM_REGISTRY}
# 国内镜像下载大包（如 next 的 43MB tarball）容易超时，放宽容错
RUN corepack enable \
 && printf 'registry=%s\nfetch-timeout=300000\nfetch-retries=6\nnetwork-concurrency=4\n' "$NPM_REGISTRY" > /root/.npmrc \
 && npm config set registry "$NPM_REGISTRY" --location=global
WORKDIR /app

FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

FROM base AS builder
# 默认留空 = 走同源，镜像不绑定任何域名
ARG NEXT_PUBLIC_API_BASE_URL=""
# 限制 Node 堆上限：小内存机器上构建时不会被 OOM 杀掉
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL} \
    NEXT_TELEMETRY_DISABLED=1 \
    NODE_OPTIONS=--max-old-space-size=1024
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN pnpm build

FROM node:22-alpine AS runner
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
WORKDIR /app
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
