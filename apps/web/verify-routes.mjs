
const routes = ["/","/features","/about","/features/merge","/features/tasks","/features/transition","/features/style","/features/format","/features/data","/features/references"];
(async () => {
  let fail = 0;
  for (const route of routes) {
    try {
      const res = await fetch("http://127.0.0.1:3000" + route);
      const html = await res.text();
      const ok = res.status === 200 && html.length > 5000;
      if (!ok) fail++;
      console.log((ok ? "OK  " : "BAD ") + route.padEnd(26) + "HTTP " + res.status + "  " + html.length + " bytes");
    } catch (e) { fail++; console.log("FAIL " + route + " " + e.message); }
  }
  const home = await (await fetch("http://127.0.0.1:3000/")).text();
  console.log("--- 首页内容检查 ---");
  console.log((home.includes("大肥鱼小组工作台") ? "OK  " : "MISS ") + "品牌名");
  for (const s of ["merge","tasks","transition","style","format","data","references"]) {
    const m = home.includes("/features/" + s);
    if (!m) fail++;
    console.log((m ? "OK  " : "MISS ") + "/features/" + s);
  }
  const notFound = await fetch("http://127.0.0.1:3000/features/nope");
  console.log("未知 slug -> HTTP " + notFound.status + (notFound.status === 404 ? " (符合预期)" : " (异常)"));
  if (notFound.status !== 404) fail++;
  console.log("失败项总计: " + fail);
})();
