// Minimal type shims to satisfy editor diagnostics

declare module 'react' {
  export type ChangeEvent<T = Element> = any;
  export const useState: any;
  const React: any;
  export default React;
}

declare module 'react/jsx-runtime' {
  export const jsx: any;
  export const jsxs: any;
  export const Fragment: any;
}

declare module 'lucide-react' {
  export const Upload: any;
  export const Play: any;
  export const Download: any;
  export const FileText: any;
  export const Settings: any;
  export const BarChart3: any;
  export const AlertCircle: any;
  export const CheckCircle: any;
  export const Loader: any;
}

declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}