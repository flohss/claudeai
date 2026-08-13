using System;
using System.Collections.Generic;
using UnityEngine;

namespace CharacterCustomization
{
    [Serializable]
    public class CharacterData
    {
        public string characterId = Guid.NewGuid().ToString();

        public List<MorphValue> morphs = new List<MorphValue>();

        public Color skinColor = Color.white;
        public string hairId = string.Empty;
        public Color hairColor = Color.black;

        public List<EquippedItem> equippedItems = new List<EquippedItem>();
    }

    [Serializable]
    public struct MorphValue
    {
        public string sliderId;
        public float weight;
    }

    [Serializable]
    public struct EquippedItem
    {
        public EquipmentSlot slot;
        public string itemId;
        public Color tint;
    }
}
