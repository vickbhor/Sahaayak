import React from 'react';

function Logo({ size = 36 }) {
  const gradId = 'sahaayakLogoGrad';
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="40" height="40" rx="11" fill={`url(#${gradId})`} />
      <path
        d="M7 21H12.5L15 12L20.5 28L24 21H27.5"
        stroke="white"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <circle cx="32" cy="21" r="2.6" fill="#E8A33D" />
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
          <stop stopColor="#1677FF" />
          <stop offset="1" stopColor="#0A3F9E" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export default Logo;
