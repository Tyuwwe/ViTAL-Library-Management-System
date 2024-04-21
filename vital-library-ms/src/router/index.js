import { createRouter, createWebHistory, createWebHashHistory } from 'vue-router';

const routes = [
    {
        path: "/",
        component: () => import("@/pages/login.vue"),
    },
    // for Normal Users
    {
        path: "/login-user",
        component: () => import("@/pages/user/login-user.vue"),
    },
    {
        path: "/index-user",
        component: () => import("@/pages/user/index-user.vue"),
    },
    {
        path: "/book/:id",
        name: "bookDetail",
        component: () => import("@/pages/user/bookDetailed.vue"),
        props: true,
    },
    {
        path: "/user/:id/name/:name?",
        name: "member",
        component: () => import("@/pages/user.vue")
    },
    // for admin
    {
        path: "/login-admin",
        component: () => import("@/pages/admin/login-admin.vue")
    }
    // ... 其他路由配置
];

const router = createRouter({
    history: createWebHashHistory(),
    routes, // 简写，相当于 routes: routes
});

export default router;