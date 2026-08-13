using System.IO;
using UnityEngine;

namespace CharacterCustomization
{
    public static class CharacterSaveSystem
    {
        private static string GetPath(string characterId)
        {
            return Path.Combine(Application.persistentDataPath, $"character_{characterId}.json");
        }

        public static void Save(CharacterData data)
        {
            var json = JsonUtility.ToJson(data, true);
            File.WriteAllText(GetPath(data.characterId), json);
        }

        public static CharacterData Load(string characterId)
        {
            var path = GetPath(characterId);
            if (!File.Exists(path))
            {
                return null;
            }

            return JsonUtility.FromJson<CharacterData>(File.ReadAllText(path));
        }
    }
}
