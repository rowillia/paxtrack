import dynamic from "next/dynamic";

export default dynamic(() => import("../components/Map"), { ssr: false });
