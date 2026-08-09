import { useRef, type ChangeEvent } from "react";
import { Button } from "./Button";

interface FileUploadProps {
  label: string;
  description: string;
  accept?: string;
  multiple?: boolean;
  disabled?: boolean;
  disabledLabel?: string;
  onFiles: (files: File[]) => void;
}

export function FileUpload({
  label,
  description,
  accept,
  multiple = false,
  disabled = false,
  disabledLabel = "当前不可替换",
  onFiles,
}: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const files = event.target.files ? Array.from(event.target.files) : [];
    if (files.length) onFiles(files);
    event.target.value = "";
  }
  return (
    <div className={`upload-box ${disabled ? "is-disabled" : ""}`}>
      <div className="upload-icon">↥</div>
      <strong>{label}</strong>
      <p>{description}</p>
      <input
        ref={inputRef}
        className="visually-hidden"
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={disabled}
        onChange={handleChange}
      />
      <Button type="button" disabled={disabled} onClick={() => inputRef.current?.click()}>
        {disabled ? disabledLabel : "选择文件"}
      </Button>
    </div>
  );
}
