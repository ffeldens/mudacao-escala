import type { MetadataRoute } from "next";

const BASE_URL = "https://simulaescala.mudacao.com.br";

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();

  return [
    {
      url: `${BASE_URL}/`,
      lastModified,
      changeFrequency: "weekly",
      priority: 1.0,
    },
    {
      url: `${BASE_URL}/simulador`,
      lastModified,
      changeFrequency: "weekly",
      priority: 0.9,
    },
    {
      url: `${BASE_URL}/precos`,
      lastModified,
      changeFrequency: "monthly",
      priority: 0.8,
    },
  ];
}
