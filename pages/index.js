import { server } from "../config";

import Head from "next/head";
import Header from "@components/Header";

export default function Home() {
  return (
    <div className="container">
      <Head>
        <title>Antiviral Tracker</title>
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <main>
        <Header title="Antiviral Tracker" />
      </main>
    </div>
  );
}
