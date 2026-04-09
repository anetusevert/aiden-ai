'use client';

import { type ChangeEvent, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/AuthContext';
import { apiClient } from '@/lib/apiClient';
import { UserAvatar } from '@/components/UserAvatar';
import { motion } from 'framer-motion';
import { fadeUp } from '@/lib/motion';
import { useTranslations } from 'next-intl';
import styles from './page.module.css';

const AVATAR_SIZE = 256;
const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;

function getRoleBadgeClass(role: string) {
  switch (role) {
    case 'ADMIN':
      return 'account-menu-role account-menu-role-admin';
    case 'EDITOR':
      return 'account-menu-role account-menu-role-editor';
    default:
      return 'account-menu-role account-menu-role-viewer';
  }
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ''));
    reader.onerror = () => reject(new Error('Failed to read image.'));
    reader.readAsDataURL(file);
  });
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error('Failed to load image.'));
    image.src = src;
  });
}

async function prepareAvatarDataUrl(file: File): Promise<string> {
  const source = await readFileAsDataUrl(file);
  const image = await loadImage(source);
  const cropSize = Math.min(image.width, image.height);
  const offsetX = Math.max(0, (image.width - cropSize) / 2);
  const offsetY = Math.max(0, (image.height - cropSize) / 2);
  const canvas = document.createElement('canvas');

  canvas.width = AVATAR_SIZE;
  canvas.height = AVATAR_SIZE;

  const context = canvas.getContext('2d');
  if (!context) {
    throw new Error('Your browser could not process this image.');
  }

  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = 'high';
  context.drawImage(
    image,
    offsetX,
    offsetY,
    cropSize,
    cropSize,
    0,
    0,
    AVATAR_SIZE,
    AVATAR_SIZE
  );

  return canvas.toDataURL('image/jpeg', 0.86);
}

export default function AccountPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, logout, logoutAll, refreshUser } =
    useAuth();
  const t = useTranslations('common');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const roleLabel = (role: string) => {
    if (role === 'ADMIN') return t('admin');
    if (role === 'EDITOR') return t('editor');
    return t('viewer');
  };

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  const profileItems = useMemo(
    () =>
      user
        ? [
            {
              label: t('fullName'),
              value: user.full_name || t('notSet'),
            },
            {
              label: t('email'),
              value: user.email || 'N/A',
            },
            {
              label: t('role'),
              value: roleLabel(user.role),
            },
            {
              label: t('userId'),
              value: user.user_id,
              mono: true,
            },
          ]
        : [],
    [t, user]
  );

  const permissions = useMemo(
    () =>
      user
        ? [
            { label: t('view'), allowed: true },
            {
              label: t('edit'),
              allowed: user.role === 'ADMIN' || user.role === 'EDITOR',
            },
            {
              label: t('manage'),
              allowed: user.role === 'ADMIN',
            },
          ]
        : [],
    [t, user]
  );

  if (isLoading) {
    return <div className="loading">Loading...</div>;
  }

  if (!user) {
    return null;
  }

  const handleAvatarPicker = () => {
    if (!isUploadingAvatar) {
      fileInputRef.current?.click();
    }
  };

  const handleAvatarSelected = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';

    if (!file) {
      return;
    }

    setUploadMessage(null);
    setUploadError(null);

    if (!file.type.startsWith('image/')) {
      setUploadError('Please choose a PNG, JPG, or other image file.');
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setUploadError('Please choose an image smaller than 5 MB.');
      return;
    }

    setIsUploadingAvatar(true);

    try {
      const avatarUrl = await prepareAvatarDataUrl(file);
      await apiClient.updateMyAvatar(avatarUrl);
      await refreshUser();
      setUploadMessage('Profile photo saved.');
    } catch (error) {
      setUploadError(
        error instanceof Error ? error.message : t('uploadFailed')
      );
    } finally {
      setIsUploadingAvatar(false);
    }
  };

  const handleRemoveAvatar = async () => {
    setUploadMessage(null);
    setUploadError(null);
    setIsUploadingAvatar(true);

    try {
      await apiClient.updateMyAvatar(null);
      await refreshUser();
      setUploadMessage('Profile photo removed.');
    } catch (error) {
      setUploadError(
        error instanceof Error ? error.message : t('uploadFailed')
      );
    } finally {
      setIsUploadingAvatar(false);
    }
  };

  return (
    <motion.div {...fadeUp} className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerCopy}>
          <h1 className={styles.headerTitle}>{t('accountTitle')}</h1>
          <p className={styles.headerSubtitle}>{t('accountSubtitle')}</p>
        </div>
      </div>

      <div className={styles.contentGrid}>
        <div className={`${styles.column} ${styles.leftColumn}`}>
          <section className={`card ${styles.panel} ${styles.heroCard}`}>
            <div className={styles.heroMain}>
              <div className={styles.avatarWrap}>
                <UserAvatar user={user} size="xl" showRing />
                <button
                  type="button"
                  className={styles.avatarButton}
                  onClick={handleAvatarPicker}
                  disabled={isUploadingAvatar}
                  title={isUploadingAvatar ? t('uploading') : t('upload')}
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.75"
                  >
                    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                    <circle cx="12" cy="13" r="4" />
                  </svg>
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  className={styles.hiddenInput}
                  onChange={handleAvatarSelected}
                />
              </div>

              <div className={styles.userMeta}>
                <h2 className={styles.userName}>{user.full_name || 'User'}</h2>
                <div className={styles.userEmail}>{user.email}</div>
                <span className={getRoleBadgeClass(user.role)}>
                  {roleLabel(user.role)}
                </span>
              </div>
            </div>

            <div className={styles.heroFooter}>
              <span
                className={`${styles.statusText} ${uploadError ? styles.statusError : ''}`}
              >
                {uploadError ||
                  uploadMessage ||
                  'Upload a square profile image and it will stay after refresh.'}
              </span>

              <div className={styles.actionRow}>
                <button
                  type="button"
                  onClick={handleAvatarPicker}
                  className="btn btn-outline"
                  disabled={isUploadingAvatar}
                >
                  {isUploadingAvatar ? t('uploading') : t('upload')}
                </button>
                {user.avatar_url ? (
                  <button
                    type="button"
                    onClick={handleRemoveAvatar}
                    className="btn btn-ghost"
                    disabled={isUploadingAvatar}
                  >
                    {t('remove')}
                  </button>
                ) : null}
              </div>
            </div>
          </section>

          <section className={`card ${styles.panel}`}>
            <div className={styles.sectionHeader}>
              <h3 className={styles.sectionTitle}>{t('profileInformation')}</h3>
            </div>

            <div className={styles.profileGrid}>
              {profileItems.map(item => (
                <div key={item.label} className={styles.infoTile}>
                  <span className={styles.infoLabel}>{item.label}</span>
                  <span
                    className={`${styles.infoValue} ${item.mono ? styles.monoValue : ''}`}
                  >
                    {item.value}
                  </span>
                </div>
              ))}
            </div>
          </section>
        </div>

        <div className={`${styles.column} ${styles.rightColumn}`}>
          <section className={`card ${styles.panel}`}>
            <div className={styles.sectionHeader}>
              <h3 className={styles.sectionTitle}>{t('permissions')}</h3>
            </div>

            <div className={styles.permissionsGrid}>
              {permissions.map(item => (
                <div key={item.label} className={styles.permissionTile}>
                  <span className={styles.permissionLabel}>{item.label}</span>
                  <div className={styles.permissionValue}>
                    <span>{item.allowed ? t('yes') : t('no')}</span>
                    <span
                      className={`badge ${item.allowed ? 'badge-success' : 'badge-error'}`}
                    >
                      {item.allowed ? t('yes') : t('no')}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className={`card ${styles.panel}`}>
            <div className={styles.sectionHeader}>
              <h3 className={styles.sectionTitle}>{t('security')}</h3>
            </div>

            <div className={styles.securityGrid}>
              <div className={styles.securityTile}>
                <div className={styles.securityCopy}>
                  <span className={styles.securityLabel}>
                    {t('authentication')}
                  </span>
                  <span className={styles.securityHint}>
                    Your session is protected with httpOnly cookie auth.
                  </span>
                </div>
                <span className="badge badge-success">{t('secureCookie')}</span>
              </div>
            </div>

            <div className={styles.securityActions}>
              <button onClick={logout} className="btn btn-outline">
                {t('signOut')}
              </button>
              <button
                onClick={logoutAll}
                className="btn btn-outline"
                title={t('signOutAllDevicesTitle')}
              >
                {t('signOutEverywhere')}
              </button>
            </div>
          </section>
        </div>
      </div>
    </motion.div>
  );
}
