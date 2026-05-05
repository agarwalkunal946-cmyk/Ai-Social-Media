function SvgIcon({ size = 20, className = "", viewBox = "0 0 24 24", children }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox={viewBox}
      fill="currentColor"
      aria-hidden="true"
      className={className}
    >
      {children}
    </svg>
  );
}

export function InstagramBrandIcon({ size = 20, className = "" }) {
  return (
    <SvgIcon size={size} className={className}>
      <path d="M7.75 2h8.5A5.75 5.75 0 0 1 22 7.75v8.5A5.75 5.75 0 0 1 16.25 22h-8.5A5.75 5.75 0 0 1 2 16.25v-8.5A5.75 5.75 0 0 1 7.75 2Zm0 1.8A3.95 3.95 0 0 0 3.8 7.75v8.5A3.95 3.95 0 0 0 7.75 20.2h8.5A3.95 3.95 0 0 0 20.2 16.25v-8.5A3.95 3.95 0 0 0 16.25 3.8Zm4.25 2.45a5.8 5.8 0 1 1 0 11.6 5.8 5.8 0 0 1 0-11.6Zm0 1.8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm5.25-.97a1.2 1.2 0 1 1 0 2.4 1.2 1.2 0 0 1 0-2.4Z" />
    </SvgIcon>
  );
}

export function YouTubeBrandIcon({ size = 20, className = "" }) {
  return (
    <SvgIcon size={size} className={className}>
      <path d="M23.498 6.186a2.997 2.997 0 0 0-2.111-2.123C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.387.518A2.997 2.997 0 0 0 .502 6.186 31.03 31.03 0 0 0 0 12a31.03 31.03 0 0 0 .502 5.814 2.997 2.997 0 0 0 2.111 2.123c1.882.518 9.387.518 9.387.518s7.505 0 9.387-.518a2.997 2.997 0 0 0 2.111-2.123A31.03 31.03 0 0 0 24 12a31.03 31.03 0 0 0-.502-5.814ZM9.75 15.568V8.432L15.955 12 9.75 15.568Z" />
    </SvgIcon>
  );
}

export function XBrandIcon({ size = 20, className = "" }) {
  return (
    <SvgIcon size={size} className={className}>
      <path d="M18.901 1.153h3.68l-8.04 9.19 9.458 12.504H16.59l-5.803-7.584-6.638 7.584H.468l8.6-9.83L0 1.153h7.595l5.242 6.932L18.901 1.153Zm-1.29 19.489h2.038L6.487 3.236H4.3l13.31 17.406Z" />
    </SvgIcon>
  );
}

export const platformBrandIcons = {
  instagram: InstagramBrandIcon,
  youtube: YouTubeBrandIcon,
  x: XBrandIcon,
};
