import { server } from '../config';

import Head from 'next/head'
import Header from '@components/Header'

export async function getStaticProps() {
  const res = await fetch(`${server}/data/NY/data.json`)
  const json = await res.json()
  return { props: {data: json} }
}

function latest(obj) {
  var largest = Object.keys(obj).sort().reverse()[0]
  return obj[largest]
}


export default function Home({ data }) {
  const total_courses = latest(data.total_courses)
  const courses_available = latest(data.courses_available)
  const courses_delivered = latest(data.courses_delivered)
  const stats = Object.keys(total_courses).map(key =>
    <li>{key}</li>
  )

  return (
    <div className="container">
      <Head>
        <title>Antiviral Tracker</title>
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main>
        <Header title="Antiviral Tracker" />
        <h1>Total Courses Supplied</h1>
        <ul>
          {Object.keys(total_courses).map(key => 
            <li key={key}>{key}: {total_courses[key]}</li>
          )}
        </ul>
        <h1>Courses Delivered</h1>
        <ul>
          {Object.keys(courses_delivered).map(key => 
            <li key={key}>{key}: {courses_delivered[key]}</li>
          )}
        </ul>
        <h1>Courses Available</h1>
        <ul>
          {Object.keys(courses_available).map(key => 
            <li key={key}>{key}: {courses_available[key]}</li>
          )}
        </ul>
      </main>
    </div>
  )
}
