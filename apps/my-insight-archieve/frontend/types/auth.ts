export type LoginResponse = {
  admin: { id: string; username: string };
};

export type MeResponse = {
  adminId: string;
  username: string;
};
