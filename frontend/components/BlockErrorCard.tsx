interface BlockErrorCardProps {
  blockName: string;
  error: string;
  errorCode: string;
  onRetry?: () => void;
}

export function BlockErrorCard({
  blockName,
  error,
  errorCode,
  onRetry,
}: BlockErrorCardProps) {
  return (
    <div className="rounded-card border border-amber-200 bg-amber-50 p-4">
      <div className="flex items-start gap-3">
        <span className="text-amber-600" aria-hidden="true">
          ⚠
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-sans text-[14px] font-semibold text-amber-800">{blockName}</p>
          <p className="mt-1 font-sans text-[14px] text-amber-800">{error}</p>
          <p className="mt-2 font-sans text-[12px] text-amber-600">Ref: {errorCode}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-3 rounded-button bg-charcoal px-3 py-1.5 font-sans text-[13px] font-medium text-workspace transition-opacity hover:opacity-90"
            >
              Try again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
