"use client";

import { Component, type ReactNode, type ErrorInfo } from "react";

interface Props {
  children: ReactNode;
  fallbackHeight?: string;
}

interface State {
  hasError: boolean;
}

export default class ChartErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("[ChartErrorBoundary]", error, errorInfo.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="bg-gray-50 border border-gray-200 rounded-2xl flex items-center justify-center"
          style={{ minHeight: this.props.fallbackHeight ?? "300px" }}
        >
          <div className="text-center space-y-2 p-6">
            <p className="text-gray-400 text-sm">图表加载失败</p>
            <button
              onClick={() => this.setState({ hasError: false })}
              className="text-brand-600 hover:underline text-xs"
            >
              点击重试
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
