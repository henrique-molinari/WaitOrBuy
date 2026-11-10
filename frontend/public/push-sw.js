// Service worker de push do WaitOrBuy. Recebe o payload do FCM (notification + data) e mostra a notificação.
// Com a aba visível o app já avisa na tela (toast), então não duplica.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("push", (e) => {
  let d = {}; try { d = e.data.json(); } catch { /* payload vazio */ }
  const n = d.notification || {}, x = d.data || {};
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((cs) => {
    if (cs.some((c) => c.visibilityState === "visible")) return;
    return self.registration.showNotification(n.title || x.title || "WaitOrBuy", {
      body: n.body || x.body || "", icon: "/favicon.svg", badge: "/favicon.svg",
      tag: x.game_id ? `jogo-${x.game_id}` : "waitorbuy", data: { url: x.game_id ? `/#/jogo/${x.game_id}` : "/#/avisos" },
    });
  }));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "/#/avisos";
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((cs) => {
    const c = cs[0];
    return c ? c.focus().then(() => c.navigate(url)) : self.clients.openWindow(url);
  }));
});
