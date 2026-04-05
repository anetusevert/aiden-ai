'use client';

import { useEffect } from 'react';
import { useNavigation } from '@/components/NavigationLoader';

export default function NewDocumentRedirectPage() {
  const { navigateTo } = useNavigation();

  useEffect(() => {
    navigateTo('/documents');
  }, [navigateTo]);

  return null;
}
