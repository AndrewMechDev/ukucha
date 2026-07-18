import type { ReactNode } from "react";

type PanelModalProps = {
  eyebrow: string;
  title: string;
  titleId: string;
  onClose: () => void;
  children: ReactNode;
  meta?: ReactNode;
  actions?: ReactNode;
  className?: string;
};

const closeIcon = (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="m6 6 12 12M18 6 6 18" />
  </svg>
);

export default function PanelModal({
  eyebrow,
  title,
  titleId,
  onClose,
  children,
  meta,
  actions,
  className = "",
}: PanelModalProps) {
  return (
    <div className="panel-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className={`panel-modal ${className}`.trim()}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="panel-modal__header">
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h1 id={titleId}>{title}</h1>
            {meta}
          </div>
          <div className="panel-modal__actions">
            {actions}
            <button className="panel-modal__close" type="button" onClick={onClose} aria-label={`Cerrar ${title.toLowerCase()}`}>
              {closeIcon}
            </button>
          </div>
        </header>
        <div className="panel-modal__body">{children}</div>
      </section>
    </div>
  );
}
