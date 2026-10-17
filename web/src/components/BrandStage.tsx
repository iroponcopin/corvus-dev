import { asset } from "@/lib/site";

/**
 * A model's own icon, large, as an app icon: a static image with a soft shadow and a faint reflection
 * of the backdrop below it (no WebGL). `dim` greys an archived model.
 */
export function BrandStage({
  icon,
  label,
  dim = false,
  className,
}: {
  icon: string;
  label: string;
  dim?: boolean;
  className?: string;
}) {
  return (
    <div
      className={`ac-model-stage ac-model-art ${className ?? ""}`}
      role={label ? "img" : undefined}
      aria-label={label || undefined}
      aria-hidden={label ? undefined : true}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={asset(icon)}
        alt=""
        width={340}
        height={340}
        data-dim={dim}
        style={dim ? { filter: "grayscale(0.75)", opacity: 0.62 } : undefined}
      />
    </div>
  );
}
