export default defineAppConfig({
  pages: [
    "pages/index/index",
    "pages/login/index",
    "pages/consent/index",
    "pages/upload/index",
    "pages/report/index",
    "pages/profile/index",
  ],
  window: {
    backgroundTextStyle: "light",
    navigationBarBackgroundColor: "#1a1a2e",
    navigationBarTitleText: "基因衰老分析",
    navigationBarTextStyle: "white",
    backgroundColor: "#f5f5f5",
  },
  tabBar: {
    color: "#999999",
    selectedColor: "#6366f1",
    backgroundColor: "#ffffff",
    borderStyle: "white",
    list: [
      {
        pagePath: "pages/index/index",
        text: "首页",
        iconPath: "assets/icons/home.png",
        selectedIconPath: "assets/icons/home-active.png",
      },
      {
        pagePath: "pages/upload/index",
        text: "检测",
        iconPath: "assets/icons/upload.png",
        selectedIconPath: "assets/icons/upload-active.png",
      },
      {
        pagePath: "pages/profile/index",
        text: "我的",
        iconPath: "assets/icons/profile.png",
        selectedIconPath: "assets/icons/profile-active.png",
      },
    ],
  },
  // 微信小程序专用配置
  permission: {
    "scope.userLocation": {
      desc: "用于健康数据地域分析（可选）",
    },
  },
  requiredPrivateInfos: [],
});
