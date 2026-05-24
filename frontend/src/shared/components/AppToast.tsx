import { useEffect, useRef } from "react";
import { Toast } from "primereact/toast";

import { registerAppToast } from "@/shared/toast/showToast";

export function AppToast() {
  const ref = useRef<Toast>(null);

  useEffect(() => {
    registerAppToast(ref);
  }, []);

  return <Toast ref={ref} position="top-right" />;
}
